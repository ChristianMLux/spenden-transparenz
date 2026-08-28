"""ingest_reliefweb_listing and fetch_report_bodies: idempotent listing and body fetch, exercised
against saved fixture HTML through a real local pytest-httpserver instance - the real network is
never hit in a test.

The frozen probe's requests session (pipeline/probes/probe_reliefweb.py's module-level `S`, and
its BASE constant) is redirected to the local server for the listing tests, not rewritten: the
parsing regexes run unmodified against real saved HTML, only the transport is intercepted. See
the reliefweb_server fixture below for exactly what is and is not patched.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import pytest
from core.models import Disaster, IngestionRun, Report, ReportSource
from sqlalchemy import func, select

from pipeline.jobs.reliefweb import (
    RateLimiter,
    _probe_reliefweb,
    country_iso3_from_glide_id,
    fetch_report_bodies,
    glide_id_from_disaster_url,
    ingest_reliefweb_listing,
    is_allowed_host,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "reliefweb"


async def _count(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


async def _latest_run(session, job: str) -> IngestionRun:
    return await session.scalar(
        select(IngestionRun).where(IngestionRun.job == job).order_by(IngestionRun.started_at.desc()).limit(1)
    )


# --- the host allowlist: pure function, its own tests ---------------------------------------------


@pytest.mark.parametrize(
    ("url", "allowed", "expected"),
    [
        ("https://reliefweb.int/report/x", ("reliefweb.int", "api.reliefweb.int"), True),
        ("https://api.reliefweb.int/v2/reports", ("reliefweb.int", "api.reliefweb.int"), True),
        ("https://www.reliefweb.int/report/x", ("reliefweb.int",), True),
        ("https://reliefweb.int.evil.example/report/x", ("reliefweb.int",), False),
        ("https://evilreliefweb.int/report/x", ("reliefweb.int",), False),
        ("https://notallowed.example/report/x", ("reliefweb.int",), False),
        ("not-a-url", ("reliefweb.int",), False),
        ("https://RELIEFWEB.INT/report/x", ("reliefweb.int",), True),
    ],
)
def test_is_allowed_host(url, allowed, expected):
    assert is_allowed_host(url, allowed) is expected


# --- the rate limiter: injected fake clock, never a real sleep -----------------------------------


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


def test_rate_limiter_does_not_wait_on_the_first_call():
    clock = _FakeClock()
    limiter = RateLimiter(2.0, clock=clock.now, sleep=clock.sleep)
    limiter.wait()
    assert clock.sleeps == []


def test_rate_limiter_waits_the_remaining_interval():
    clock = _FakeClock()
    limiter = RateLimiter(2.0, clock=clock.now, sleep=clock.sleep)
    limiter.wait()
    clock.t += 0.5
    limiter.wait()
    assert clock.sleeps == [1.5]


def test_rate_limiter_does_not_wait_once_the_interval_has_already_elapsed():
    clock = _FakeClock()
    limiter = RateLimiter(2.0, clock=clock.now, sleep=clock.sleep)
    limiter.wait()
    clock.t += 3.0
    limiter.wait()
    assert clock.sleeps == []


# --- GLIDE derivation -------------------------------------------------------------------------


def test_glide_id_from_disaster_url():
    assert glide_id_from_disaster_url("https://reliefweb.int/disaster/ff-2026-000162-npl") == "ff-2026-000162-npl"
    assert glide_id_from_disaster_url("https://reliefweb.int/disaster/ff-2026-000162-npl/") == "ff-2026-000162-npl"


def test_country_iso3_from_glide_id():
    assert country_iso3_from_glide_id("ff-2026-000162-npl") == "NPL"
    assert country_iso3_from_glide_id("no-country-code-here") is None


# --- ingest_reliefweb_listing: real parsers, saved fixture HTML, local server only -----------------


@pytest.fixture
def reliefweb_server(httpserver, monkeypatch):
    """Redirect the frozen probe's transport to the local httpserver, not its parsing.

    BASE covers the requests the probe builds itself (f"{BASE}/updates", f"{BASE}/country/npl").
    The S.get wrapper covers current_disasters()'s second-hop fetch, which follows the ABSOLUTE
    https://reliefweb.int/disaster/... URL it discovers inside the first page's HTML rather than
    building it from BASE - without this, that second request would still try the real network.

    current_disasters() also has a real side effect of its own: it calls dump_bytes(SRC,
    "country_npl.html", r.content), which writes into data/raw/reliefweb/ regardless of where the
    request actually went. The first version of this fixture missed that and a test run silently
    overwrote the real research artifact at data/raw/reliefweb/country_npl.html with fixture
    content - caught via `git status` and reverted (git checkout), not by a test failure. Both
    dump_bytes and dump_json are neutralised here so no test in this file can touch data/raw/
    again; pipeline/probes/ is frozen, but the disk writes it performs as a side effect of being
    a research script are exactly what a job's tests must not trigger for real.
    """
    base = httpserver.url_for("/").rstrip("/")
    monkeypatch.setattr(_probe_reliefweb, "BASE", base)
    monkeypatch.setattr(_probe_reliefweb, "dump_bytes", lambda *args, **kwargs: None)
    monkeypatch.setattr(_probe_reliefweb, "dump_json", lambda *args, **kwargs: None)

    real_get = _probe_reliefweb.S.get

    def _redirect(url, *args, **kwargs):
        parsed = urlparse(url)
        if parsed.hostname == "reliefweb.int":
            url = base + parsed.path + (f"?{parsed.query}" if parsed.query else "")
        return real_get(url, *args, **kwargs)

    monkeypatch.setattr(_probe_reliefweb.S, "get", _redirect)
    return httpserver


def _register_listing_fixtures(httpserver) -> None:
    httpserver.expect_request("/country/npl").respond_with_data(
        (FIXTURES / "country_npl.html").read_text(encoding="utf-8"), content_type="text/html"
    )
    httpserver.expect_request("/disaster/ff-2026-000162-npl").respond_with_data(
        (FIXTURES / "disaster_ff-2026-000162-npl.html").read_text(encoding="utf-8"), content_type="text/html"
    )
    httpserver.expect_request("/updates", query_string={"advanced-search": "(D52684)", "page": "0"}).respond_with_data(
        (FIXTURES / "updates_page0.html").read_text(encoding="utf-8"), content_type="text/html"
    )
    # listing() paginates until a page returns no <article> matches. An explicit, fast, real
    # empty page here (status 200, no articles) is what makes the loop stop - relying on
    # pytest-httpserver's default response for an unmatched route returned a 500, which is in
    # the probe's urllib3 Retry status_forcelist and added ~10s of retry/backoff to every test
    # here, which in turn widened the window for the shared-test-database collision described in
    # the WP-A report (another worker's session running DROP DATABASE against the same
    # pipeline/tests/conftest.py JOB_DB while this test was still mid-retry).
    httpserver.expect_request("/updates", query_string={"advanced-search": "(D52684)", "page": "1"}).respond_with_data(
        "<html><body>0 results found</body></html>", content_type="text/html"
    )


async def test_ingest_reliefweb_listing_writes_disaster_report_and_source(job_sessionmaker, session, reliefweb_server):
    _register_listing_fixtures(reliefweb_server)

    await ingest_reliefweb_listing(job_sessionmaker)

    assert await _count(session, Disaster) == 1
    disaster = await session.get(Disaster, "ff-2026-000162-npl")
    assert disaster.reliefweb_id == "D52684"
    assert disaster.country_iso3 == "NPL"
    assert disaster.name == "Nepal: Flash Floods - Aug 2026"
    assert disaster.is_active is True

    assert await _count(session, Report) == 1
    report = (await session.execute(select(Report))).scalars().first()
    assert report.url.endswith("/report/nepal/sample-report-one")
    assert report.title == "Sample Report One"
    assert report.format == "News and Press Release"
    assert report.disaster_glide_id == "ff-2026-000162-npl"
    assert report.body_text is None

    assert await _count(session, ReportSource) == 1
    source = (await session.execute(select(ReportSource))).scalars().first()
    assert source.publisher == "Save the Children"


async def test_ingest_reliefweb_listing_second_run_writes_zero_rows(job_sessionmaker, session, reliefweb_server):
    _register_listing_fixtures(reliefweb_server)
    await ingest_reliefweb_listing(job_sessionmaker)
    await ingest_reliefweb_listing(job_sessionmaker)
    run = await _latest_run(session, "ingest_reliefweb_listing")
    assert run.rows_written == 0
    assert run.status == "succeeded"


async def test_ingest_reliefweb_listing_never_deletes(job_sessionmaker, session, reliefweb_server):
    _register_listing_fixtures(reliefweb_server)
    await ingest_reliefweb_listing(job_sessionmaker)
    before = await _count(session, Report)
    await ingest_reliefweb_listing(job_sessionmaker)
    after = await _count(session, Report)
    assert after == before


# --- fetch_report_bodies: real fetch_report(), local server only ---------------------------------


async def test_fetch_report_bodies_fetches_and_stores_body_sha256(job_sessionmaker, session, httpserver):
    httpserver.expect_request("/report/nepal/sample-report-one").respond_with_data(
        (FIXTURES / "report_sample_one.html").read_text(encoding="utf-8"), content_type="text/html"
    )
    url = httpserver.url_for("/report/nepal/sample-report-one")

    async with job_sessionmaker() as write:
        write.add(Report(url=url, title="Sample Report One", disaster_glide_id=None))
        await write.commit()

    await fetch_report_bodies(job_sessionmaker, allowed_hosts=("localhost",), min_interval_s=0.0)

    report = (await session.execute(select(Report).where(Report.url == url))).scalar_one()
    assert report.body_text is not None
    assert "Save the Children" in report.body_text
    assert report.body_sha256 == hashlib.sha256(report.body_text.encode("utf-8")).hexdigest()
    assert report.body_fetched_at is not None
    assert report.extraction_attempts == 1
    assert report.last_extraction_error is None


async def test_fetch_report_bodies_second_run_does_not_reselect_a_fetched_report(job_sessionmaker, session, httpserver):
    httpserver.expect_request("/report/nepal/sample-report-one").respond_with_data(
        (FIXTURES / "report_sample_one.html").read_text(encoding="utf-8"), content_type="text/html"
    )
    url = httpserver.url_for("/report/nepal/sample-report-one")

    async with job_sessionmaker() as write:
        write.add(Report(url=url, title="Sample Report One", disaster_glide_id=None))
        await write.commit()

    await fetch_report_bodies(job_sessionmaker, allowed_hosts=("localhost",), min_interval_s=0.0)
    await fetch_report_bodies(job_sessionmaker, allowed_hosts=("localhost",), min_interval_s=0.0)

    run = await _latest_run(session, "fetch_report_bodies")
    assert run.rows_written == 0


async def test_fetch_report_bodies_never_fetches_a_disallowed_host(job_sessionmaker, session):
    """A report we are not allowed to fetch is not a candidate, so nothing is attempted on it.

    Changed from the original contract, which counted it as rejected and incremented
    extraction_attempts. Both were wrong: nothing was attempted, so there is no attempt to record,
    and after three runs the row would have been excluded for having "failed" three times it never
    tried.
    """
    calls: list[str] = []

    def _must_not_be_called(url: str) -> dict:
        calls.append(url)
        raise AssertionError("fetch_fn must not be called for a disallowed host")

    async with job_sessionmaker() as write:
        write.add(Report(url="https://evil.example/report/x", title="Evil", disaster_glide_id=None))
        await write.commit()

    await fetch_report_bodies(
        job_sessionmaker, fetch_fn=_must_not_be_called, allowed_hosts=("reliefweb.int",), min_interval_s=0.0
    )

    assert calls == []
    report = (await session.execute(select(Report).where(Report.url == "https://evil.example/report/x"))).scalar_one()
    assert report.body_text is None
    assert report.extraction_attempts == 0
    assert report.last_extraction_error is None


async def test_a_disallowed_host_does_not_consume_the_per_run_budget(job_sessionmaker, session):
    """The bug this whole change exists for.

    ingest_orgs writes a report row per researched source_url - org sites, press releases, news -
    and the limit used to be applied before the host check. Those rows filled the entire budget and
    every reliefweb.int report went unfetched, run after run, while the job reported success.
    """
    fetched: list[str] = []

    def _fetch(url: str) -> dict:
        fetched.append(url)
        return {"status": 200, "text": "body text", "title": "T", "date": None}

    async with job_sessionmaker() as write:
        for index in range(3):
            write.add(Report(url=f"https://not-ours-{index}.example/x", title=None, disaster_glide_id=None))
        write.add(Report(url="https://reliefweb.int/report/nepal/wanted", title=None, disaster_glide_id=None))
        await write.commit()

    # A budget of two, with three unfetchable rows sorted ahead of the one that matters.
    await fetch_report_bodies(
        job_sessionmaker,
        fetch_fn=_fetch,
        allowed_hosts=("reliefweb.int",),
        min_interval_s=0.0,
        max_reports=2,
    )

    assert fetched == ["https://reliefweb.int/report/nepal/wanted"]
    run = await _latest_run(session, "fetch_report_bodies")
    assert run.rows_written == 1


async def test_fetch_report_bodies_stops_retrying_after_three_attempts(job_sessionmaker, session):
    async with job_sessionmaker() as write:
        write.add(
            Report(
                url="https://reliefweb.int/report/dead",
                title="Dead link",
                disaster_glide_id=None,
                extraction_attempts=3,
            )
        )
        await write.commit()

    def _must_not_be_called(url: str) -> dict:
        raise AssertionError("a report already at 3 attempts must not be re-selected")

    await fetch_report_bodies(job_sessionmaker, fetch_fn=_must_not_be_called, min_interval_s=0.0)


async def test_fetch_report_bodies_respects_max_reports_per_run(job_sessionmaker, session):
    fetched: list[str] = []

    def _fake_fetch(url: str) -> dict:
        fetched.append(url)
        return {"url": url, "status": 200, "title": "t", "date": None, "text": f"body for {url}", "text_len": 10}

    async with job_sessionmaker() as write:
        for i in range(5):
            write.add(Report(url=f"https://reliefweb.int/report/{i}", title=f"r{i}", disaster_glide_id=None))
        await write.commit()

    await fetch_report_bodies(job_sessionmaker, fetch_fn=_fake_fetch, max_reports=2, min_interval_s=0.0)

    assert len(fetched) == 2


async def test_fetch_report_bodies_paces_calls_by_the_injected_clock(job_sessionmaker, session):
    clock = _FakeClock()

    def _fake_fetch(url: str) -> dict:
        return {"url": url, "status": 200, "title": "t", "date": None, "text": f"body for {url}", "text_len": 10}

    async with job_sessionmaker() as write:
        for i in range(3):
            write.add(Report(url=f"https://reliefweb.int/report/{i}", title=f"r{i}", disaster_glide_id=None))
        await write.commit()

    await fetch_report_bodies(
        job_sessionmaker, fetch_fn=_fake_fetch, min_interval_s=2.0, clock=clock.now, sleep=clock.sleep
    )

    # The fake clock never advances on its own between calls, so every call after the first has
    # to wait the full interval.
    assert clock.sleeps == [2.0, 2.0]


async def test_fetch_report_bodies_never_deletes(job_sessionmaker, session):
    def _fake_fetch(url: str) -> dict:
        return {"url": url, "status": 200, "title": "t", "date": None, "text": "body", "text_len": 4}

    async with job_sessionmaker() as write:
        write.add(Report(url="https://reliefweb.int/report/a", title="a", disaster_glide_id=None))
        await write.commit()

    await fetch_report_bodies(job_sessionmaker, fetch_fn=_fake_fetch, min_interval_s=0.0)
    assert await _count(session, Report) == 1
    report = (await session.execute(select(Report))).scalar_one()
    assert report.extraction_attempts == 1
