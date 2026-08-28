"""ingest_reliefweb_listing and fetch_report_bodies: disaster + report metadata from ReliefWeb's
website (no API - see pipeline/probes/probe_reliefweb.py's own docstring for why), and report full
text for extraction, fetched at a deliberate pace with an honest User-Agent and a host allowlist.

pipeline/probes/ is deliberately not a Python package (its files import each other with a bare
`from common import ...`, matching how they were run as standalone research scripts), so
current_disasters(), listing() and fetch_report() are loaded by file location rather than a normal
import - see _load_probe_module. The parsers themselves are not touched: "reuse the frozen probe
functions rather than rewriting the parsers" (plan, Task A-3).

GLIDE codes: ReliefWeb's own listing gives no separate GLIDE field (measured against
data/raw/reliefweb/disasters_current.json), but the disaster page URL slug always is the GLIDE
code (https://reliefweb.int/disaster/ff-2026-000162-npl -> ff-2026-000162-npl), and GLIDE codes are
standardised to end with the ISO3 country code as their last hyphen-separated segment - both
derived here, neither invented.

This job is single-threaded, sequential batch work run from a CLI/cron process, not a request
handler competing with other async tasks on a shared event loop, so fetch_fn and the rate
limiter's sleep are deliberately blocking calls (as the plan directs: "measure with a monotonic
clock, sleep the remainder") rather than async ones.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlparse

from core.logging import get_logger
from core.models import Disaster, Report, ReportSource
from core.settings import get_settings
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pipeline.runs import RunHandle, run_context

log = get_logger("ingest_reliefweb")

PROBES_DIR = Path(__file__).resolve().parents[1] / "probes"

MAX_EXTRACTION_ATTEMPTS = 3


def _load_probe_module(name: str) -> ModuleType:
    """Add pipeline/probes to sys.path once (so the module's own `from common import ...`
    resolves the way it does when the probe is run as a script) and load it by file location,
    since probes/ has no __init__.py and is not meant to become an importable package."""
    if str(PROBES_DIR) not in sys.path:
        sys.path.insert(0, str(PROBES_DIR))
    spec = importlib.util.spec_from_file_location(f"pipeline_probes_{name}", PROBES_DIR / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load probe module {name!r} from {PROBES_DIR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_probe_reliefweb = _load_probe_module("probe_reliefweb")
current_disasters = _probe_reliefweb.current_disasters
listing = _probe_reliefweb.listing
fetch_report = _probe_reliefweb.fetch_report


# --- the host allowlist: its own function, its own tests -----------------------------------------


def is_allowed_host(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    """True only if the URL's parsed hostname is exactly one of allowed_hosts, or a proper
    subdomain of one (a dot-prefixed suffix match) - never checked against the raw URL string.

    "https://reliefweb.int.evil.example/" contains "reliefweb.int" as a literal substring, so a
    check like `"reliefweb.int" in url` or `host.endswith("reliefweb.int")` would wrongly accept
    it. Its parsed host is "reliefweb.int.evil.example", which is neither equal to "reliefweb.int"
    nor a dot-prefixed suffix of it (it ends in ".evil.example") - the classic lookalike-domain
    hole this function exists to close.
    """
    host = urlparse(url).hostname
    if not host:
        return False
    host = host.lower()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


# --- the rate limiter: injected clock/sleep so tests never actually wait -------------------------


class RateLimiter:
    """At least min_interval_s between calls to wait(). Measured with a monotonic clock; the
    remainder of the interval is slept, never busy-waited. clock/sleep are injected so a test can
    supply a fake clock instead of a real 2-second sleep on every call.
    """

    def __init__(
        self,
        min_interval_s: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval_s = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._last_call: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last_call is not None:
            remaining = self._min_interval_s - (now - self._last_call)
            if remaining > 0:
                self._sleep(remaining)
        self._last_call = self._clock()


# --- shared bulk-upsert helper (mutable rows, same shape as seed_reference/orgs) -----------------


async def _upsert(
    session: AsyncSession,
    model: type,
    rows: list[dict[str, Any]],
    key: str,
    columns: tuple[str, ...],
) -> int:
    """One statement for the whole batch. See pipeline/jobs/seed_reference.py:_upsert."""
    if not rows:
        return 0
    statement = insert(model).values(rows)
    changed = or_(*[getattr(model, column).is_distinct_from(statement.excluded[column]) for column in columns])
    statement = statement.on_conflict_do_update(
        index_elements=[key],
        set_={column: statement.excluded[column] for column in columns},
        where=changed,
    ).returning(getattr(model, key))
    result = await session.execute(statement)
    return len(result.scalars().all())


async def _insert_ignore(
    session: AsyncSession, model: type, rows: list[dict[str, Any]], index_elements: list[str]
) -> int:
    """report_source has a composite primary key (report_id, publisher), not a single synthetic
    id column to RETURNING, so this counts affected rows directly: Postgres's INSERT command tag
    - and rowcount here - counts only rows actually inserted, never ones ON CONFLICT DO NOTHING
    skipped."""
    if not rows:
        return 0
    statement = insert(model).values(rows).on_conflict_do_nothing(index_elements=index_elements)
    result = await session.execute(statement)
    return result.rowcount


# --- ingest_reliefweb_listing ----------------------------------------------------------------


DISASTER_COLUMNS = ("reliefweb_id", "name", "country_iso3", "started_on", "is_active", "source_url")
REPORT_COLUMNS = ("title", "format", "published_at", "disaster_glide_id")


def glide_id_from_disaster_url(url: str) -> str:
    """https://reliefweb.int/disaster/ff-2026-000162-npl -> ff-2026-000162-npl."""
    return url.rstrip("/").rsplit("/", 1)[-1]


def country_iso3_from_glide_id(glide_id: str) -> str | None:
    """GLIDE codes end with the ISO3 country code as their last hyphen-separated segment."""
    tail = glide_id.rsplit("-", 1)[-1]
    return tail.upper() if len(tail) == 3 and tail.isalpha() else None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _disaster_row(item: dict[str, Any], run_id: Any) -> dict[str, Any] | None:
    url = item.get("url")
    if not url:
        return None
    glide_id = glide_id_from_disaster_url(url)
    disaster_id = item.get("disaster_id")
    return {
        "glide_id": glide_id,
        "reliefweb_id": f"D{disaster_id}" if disaster_id else None,
        "name": item.get("title") or glide_id,
        "country_iso3": country_iso3_from_glide_id(glide_id),
        "started_on": None,
        "is_active": True,
        "source_url": url,
        "ingestion_run_id": run_id,
    }


def _report_row(url: str, item: dict[str, Any], glide_id: str, run_id: Any) -> dict[str, Any]:
    return {
        "url": url,
        "title": item.get("title"),
        "format": item.get("format"),
        "published_at": _parse_datetime(item.get("date")),
        "disaster_glide_id": glide_id,
        "ingestion_run_id": run_id,
    }


async def ingest_reliefweb_listing(
    session_factory: async_sessionmaker[AsyncSession],
    handle: RunHandle | None = None,
    *,
    current_disasters_fn: Callable[[], tuple[list[dict[str, Any]], int]] = current_disasters,
    listing_fn: Callable[[str], tuple[dict[str, dict[str, Any]], int | None]] = listing,
) -> None:
    """Idempotent. current_disasters() finds Nepal's currently listed disasters; for each,
    listing() paginates its updates, and this upserts disaster, report (metadata only -
    body_text is fetch_report_bodies's job) and report_source. Never deletes; a report or
    disaster that drops out of a later listing simply stops being touched, it is not removed.
    """
    if handle is None:
        async with run_context(session_factory, "ingest_reliefweb_listing") as run:
            await ingest_reliefweb_listing(
                session_factory, run, current_disasters_fn=current_disasters_fn, listing_fn=listing_fn
            )
        return

    run_id = handle.id
    disasters_raw, status = current_disasters_fn()
    if status != 200:
        log.warning("reliefweb_country_page_not_200", extra={"status": status})

    disaster_rows = [row for item in disasters_raw if (row := _disaster_row(item, run_id)) is not None]

    written = 0
    skipped = 0
    report_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    async with session_factory() as session:
        disaster_written = await _upsert(session, Disaster, disaster_rows, "glide_id", DISASTER_COLUMNS)
        written += disaster_written
        skipped += len(disaster_rows) - disaster_written

        sources_by_url: dict[str, list[str]] = {}
        for item in disasters_raw:
            url = item.get("url")
            disaster_id = item.get("disaster_id")
            if not url or not disaster_id:
                continue
            glide_id = glide_id_from_disaster_url(url)
            updates, _total = listing_fn(f"(D{disaster_id})")
            for report_url, row in updates.items():
                report_rows.append(_report_row(report_url, row, glide_id, run_id))
                sources_by_url[report_url] = row.get("sources") or []

        report_written = await _upsert(session, Report, report_rows, "url", REPORT_COLUMNS)
        written += report_written
        skipped += len(report_rows) - report_written

        report_ids: dict[str, int] = {}
        if report_rows:
            urls = [row["url"] for row in report_rows]
            id_rows = await session.execute(select(Report.id, Report.url).where(Report.url.in_(urls)))
            report_ids = {url: report_id for report_id, url in id_rows}

        source_rows = [
            {"report_id": report_ids[url], "publisher": publisher}
            for url, publishers in sources_by_url.items()
            for publisher in publishers
            if url in report_ids
        ]
        source_written = await _insert_ignore(session, ReportSource, source_rows, ["report_id", "publisher"])
        written += source_written
        skipped += len(source_rows) - source_written

        await session.commit()

    handle.count(written=written, skipped=skipped)
    log.info(
        "ingest_reliefweb_listing_done",
        extra={
            "disasters": len(disaster_rows),
            "reports": len(report_rows),
            "sources": len(source_rows),
            "written": written,
            "skipped": skipped,
        },
    )


# --- fetch_report_bodies -----------------------------------------------------------------------


async def fetch_report_bodies(
    session_factory: async_sessionmaker[AsyncSession],
    handle: RunHandle | None = None,
    *,
    fetch_fn: Callable[[str], dict[str, Any]] = fetch_report,
    allowed_hosts: tuple[str, ...] | None = None,
    max_reports: int | None = None,
    min_interval_s: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Idempotent by construction: only reports with body_text IS NULL are selected, so a report
    this job already fetched is never re-selected on a later run. Fetches at most max_reports
    (settings.max_reports_per_run, default 25), at least min_interval_s apart
    (settings.reliefweb_min_interval_s, default 2.0 - a real, blocking wait against the real
    ReliefWeb host in production; tests inject a fake clock/sleep so they never actually wait),
    and only from a host in allowed_hosts (settings.allowed_fetch_hosts), checked before every
    request.
    """
    if handle is None:
        async with run_context(session_factory, "fetch_report_bodies") as run:
            await fetch_report_bodies(
                session_factory,
                run,
                fetch_fn=fetch_fn,
                allowed_hosts=allowed_hosts,
                max_reports=max_reports,
                min_interval_s=min_interval_s,
                clock=clock,
                sleep=sleep,
            )
        return

    settings = get_settings()
    hosts = allowed_hosts if allowed_hosts is not None else settings.allowed_fetch_hosts
    limit = max_reports if max_reports is not None else settings.max_reports_per_run
    interval = min_interval_s if min_interval_s is not None else settings.reliefweb_min_interval_s
    limiter = RateLimiter(interval, clock=clock, sleep=sleep)

    written = 0
    skipped = 0
    rejected = 0

    async with session_factory() as session:
        # The host filter runs BEFORE the per-run limit, not after it.
        #
        # ingest_orgs creates a report row per researched source_url - org sites, press releases,
        # news - so the table holds rows this job was never meant to fetch. With the limit applied
        # first, those rows filled the entire budget of 25 and every reliefweb.int report went
        # unfetched, run after run. The job reported success with 25 rejected, which reads like a
        # network problem rather than a selection bug.
        #
        # A report we are not allowed to fetch is not a failed candidate; it is not a candidate.
        # It gets no extraction_attempts increment, because nothing was attempted.
        unfetched = (
            (
                await session.execute(
                    select(Report)
                    .where(Report.body_text.is_(None), Report.extraction_attempts < MAX_EXTRACTION_ATTEMPTS)
                    .order_by(Report.id)
                )
            )
            .scalars()
            .all()
        )
        candidates = [report for report in unfetched if is_allowed_host(report.url, hosts)][:limit]
        not_ours = len(unfetched) - len([r for r in unfetched if is_allowed_host(r.url, hosts)])
        if not_ours:
            log.info("reports_outside_the_allowlist_skipped", extra={"count": not_ours})

        for report in candidates:
            limiter.wait()
            result = fetch_fn(report.url)
            report.extraction_attempts += 1

            if result.get("status") != 200 or not result.get("text"):
                report.last_extraction_error = f"fetch failed: status {result.get('status')}"
                skipped += 1
                continue

            body_sha256 = hashlib.sha256(result["text"].encode("utf-8")).hexdigest()
            if body_sha256 == report.body_sha256:
                # Reachable only if body_sha256 was already set without body_text (should not
                # happen in normal operation, since both are written together below) - an
                # unchanged hash is a no-op, not a rewrite, same rule as every other job here.
                skipped += 1
                continue

            report.body_text = result["text"]
            report.body_sha256 = body_sha256
            report.body_fetched_at = datetime.now(UTC)
            report.last_extraction_error = None
            written += 1

        await session.commit()

    handle.count(written=written, skipped=skipped, rejected=rejected)
    log.info(
        "fetch_report_bodies_done",
        extra={
            "candidates": len(candidates),
            "written": written,
            "skipped": skipped,
            "rejected": rejected,
        },
    )
