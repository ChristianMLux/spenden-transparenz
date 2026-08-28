"""API test fixtures.

The migration tests need a database of their own: the model tests own the main test database via
create_all, and running `alembic upgrade head` into the same schema would collide with them.

WP-C's contract tests (test_contract.py, test_responders.py, test_orgs.py, test_meta.py,
test_admin.py) get a THIRD database, migrated with Alembic (so the tests exercise the real schema,
not a hand-rolled create_all) and seeded once per session with a small, fixed dataset via the
models directly - not through the pipeline jobs, which WP-A and WP-B are still building in
parallel. See SEEDED_* constants below for what exists and under which id.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from app.main import create_app
from core.db import make_engine, make_sessionmaker
from core.models import (
    Disaster,
    District,
    IngestionRun,
    OrgAlias,
    Organisation,
    OrgDatum,
    OrgRegistration,
    OrgWarning,
    Report,
    ReportSource,
    ResponseStatement,
    StatementDistrict,
)
from httpx import ASGITransport, AsyncClient

API_DIR = Path(__file__).resolve().parents[1]
REPO = API_DIR.parents[1]

DEFAULT_SYNC_URL = "postgresql+psycopg://spenden:spenden@localhost:55432/spenden"
SCRATCH_DB_BASE = "spenden_migrations"
SEED_DB_BASE = "spenden_api_contract"


def scratch_db(base: str) -> str:
    """A database name unique to this checkout.

    Every worktree points at the same Postgres container, and the names used to be fixed. Two
    workers running their suites at the same time would then DROP the database the other was
    using, which surfaced as ConnectionDoesNotExistError and as rows vanishing between insert and
    read - in test files neither worker had touched. Hashing the repository root gives each
    checkout its own database, stable across runs so the containers do not fill up with strays.
    Override with SPENDEN_TEST_DB_SUFFIX when you want to pin one.
    """
    suffix = (
        os.environ.get("SPENDEN_TEST_DB_SUFFIX")
        or hashlib.blake2s(str(REPO).encode("utf-8"), digest_size=3).hexdigest()
    )
    return f"{base}_{suffix}"


SCRATCH_DB = scratch_db(SCRATCH_DB_BASE)
# The seeded contract database gets the same per-checkout isolation as SCRATCH_DB, for the same
# reason: two worktrees running apps/api/tests concurrently against the shared Postgres container
# would otherwise DROP and recreate each other's spenden_api_contract mid-run.
SEED_DB = scratch_db(SEED_DB_BASE)

# --- what test_contract.py, test_responders.py, test_orgs.py, test_meta.py and test_admin.py can
# rely on existing. Hardcode these ids directly in tests rather than importing them, matching the
# style the plan's own example tests use.
DISASTER_GLIDE_ID = "ff-2026-000162-npl"
NRCS_ORG_ID = "nepal-red-cross-society"  # a gap: financial_transparency.income, source_unreachable
WORLD_VISION_ORG_ID = "world-vision-nepal"  # a pledge (amount_basis=pledged), a warning
UNICEF_ORG_ID = "unicef-nepal"  # an inherited-district statement + a rejected_unverbatim one
NO_RESPONSE_ORG_ID = "some-other-ingo"  # zero statements, for has_response coverage
UNMATCHED_RAW_NAME = "Local youth club, Timure"  # org_id null: named but not identified


def base_sync_url() -> str:
    return os.environ.get("TEST_DATABASE_URL_SYNC", DEFAULT_SYNC_URL)


def _psycopg_url(url: str, database: str) -> str:
    """Turn a SQLAlchemy URL into a libpq one pointing at `database`."""
    without_driver = "postgresql://" + url.partition("://")[2]
    head, _, _ = without_driver.rpartition("/")
    return f"{head}/{database}"


@pytest.fixture(scope="session")
def scratch_db_url() -> Iterator[str]:
    """A freshly created, empty database, dropped again afterwards."""
    maintenance = _psycopg_url(base_sync_url(), "postgres")
    with psycopg.connect(maintenance, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{SCRATCH_DB}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{SCRATCH_DB}"')
    yield _psycopg_url(base_sync_url(), SCRATCH_DB).replace("postgresql://", "postgresql+psycopg://", 1)
    with psycopg.connect(maintenance, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{SCRATCH_DB}" WITH (FORCE)')


def _alembic_config(url: str) -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def alembic_config() -> Callable[[str], Config]:
    """Builds an Alembic config pointed at a given database. A fixture rather than an import,
    so the test modules do not have to make `tests` an importable package."""
    return _alembic_config


@pytest.fixture
async def client_no_db() -> AsyncIterator[AsyncClient]:
    """The stub routes serve no data, so they need no database. Building the client without one
    also proves that: a stub route that quietly queried Postgres would fail here."""
    app = create_app(database_url=None)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


@pytest.fixture(scope="session")
def migrated(scratch_db_url: str) -> str:
    """The scratch database at head. Shared by the migration tests and the API tests."""
    command.upgrade(_alembic_config(scratch_db_url), "head")
    return scratch_db_url


# --- WP-C's seeded contract database -----------------------------------------------------------


def _hash() -> str:
    return uuid.uuid4().hex


async def _seed(session_factory) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                District(code="NP0329", name="Rasuwa", admin1_code="NP03", admin1_name="Bagmati"),
                District(code="NP0328", name="Nuwakot", admin1_code="NP03", admin1_name="Bagmati"),
                District(code="NP0330", name="Dhading", admin1_code="NP03", admin1_name="Bagmati"),
                Disaster(
                    glide_id=DISASTER_GLIDE_ID,
                    reliefweb_id="D52684",
                    name="Nepal: Floods - Aug 2026",
                    country_iso3="NPL",
                    started_on=date(2026, 8, 10),
                    is_active=True,
                    source_url=f"https://reliefweb.int/disaster/{DISASTER_GLIDE_ID}",
                ),
            ]
        )

        session.add_all(
            [
                Organisation(
                    org_id=NRCS_ORG_ID,
                    name_common="Nepal Red Cross Society",
                    org_type="red_cross_movement",
                    hq_country="NP",
                    hq_city="Kathmandu",
                    website="https://www.nrcs.org",
                    last_updated=date(2026, 8, 20),
                ),
                Organisation(
                    org_id=WORLD_VISION_ORG_ID,
                    name_common="World Vision Nepal",
                    org_type="ingo",
                    hq_country="US",
                    website="https://www.worldvision.org",
                    last_updated=date(2026, 8, 18),
                ),
                Organisation(
                    org_id=UNICEF_ORG_ID,
                    name_common="UNICEF Nepal",
                    org_type="un_agency",
                    hq_country="US",
                    website="https://www.unicef.org/nepal",
                    last_updated=date(2026, 8, 15),
                ),
                Organisation(
                    org_id=NO_RESPONSE_ORG_ID,
                    name_common="Some Other INGO",
                    org_type="ingo",
                    hq_country="DE",
                    website="https://example.org",
                    last_updated=date(2026, 8, 10),
                ),
            ]
        )
        await session.flush()

        # The known, explicit gap: NRCS financial_transparency.income. This is the exact row
        # PO-3 and test_contract.py check.
        session.add(
            OrgDatum(
                org_id=NRCS_ORG_ID,
                path="financial_transparency.income",
                value=None,
                source_url=None,
                note="swc.org.np was unreachable during this research session.",
                gap_reason="source_unreachable",
                verification="unverified",
                content_hash=_hash(),
            )
        )
        # A sourced value, alongside the gap: the same organisation carries both, proving the
        # serialiser (and the API) treat them identically in shape.
        session.add(
            OrgDatum(
                org_id=NRCS_ORG_ID,
                path="names.common",
                value="Nepal Red Cross Society",
                value_type="string",
                source_url="https://www.nrcs.org",
                retrieved_at=date(2026, 8, 20),
                verification="self_reported",
                content_hash=_hash(),
            )
        )
        # The Devanagari name, rendered by the frontend in a lang="ne" span, and the acronyms the
        # board's name search has to match even though neither is a substring of the common name.
        session.add(
            OrgDatum(
                org_id=NRCS_ORG_ID,
                path="names.local_script",
                value="नेपाल रेड क्रस सोसाइटी",
                value_type="string",
                source_url="https://www.nrcs.org",
                retrieved_at=date(2026, 8, 20),
                verification="self_reported",
                content_hash=_hash(),
            )
        )
        # Schema v0.5: the donation channel. NRCS has one, World Vision has a researched gap, so
        # the board row has to render both an official link and an explicit "none found" with the
        # same weight - which is the whole point of the field.
        session.add_all(
            [
                OrgDatum(
                    org_id=NRCS_ORG_ID,
                    path="donation_channel",
                    value="https://donation.nrcs.org/",
                    value_type="string",
                    channel_type="donation_page",
                    flood_specific=False,
                    source_url="https://www.nrcs.org",
                    retrieved_at=date(2026, 8, 28),
                    quote="Ways to Donate To Nepal Redcross",
                    verification="self_reported",
                    content_hash=_hash(),
                ),
                OrgDatum(
                    org_id=WORLD_VISION_ORG_ID,
                    path="donation_channel",
                    value=None,
                    source_url=None,
                    note="No donation page on this organisation's own domain was found.",
                    gap_reason="searched_not_found",
                    verification="unverified",
                    content_hash=_hash(),
                ),
            ]
        )
        session.add_all(
            [
                OrgAlias(alias_norm="nrcs", org_id=NRCS_ORG_ID, kind="acronym"),
                OrgAlias(alias_norm="nepal red cross", org_id=NRCS_ORG_ID, kind="former_name"),
            ]
        )
        session.add(
            OrgRegistration(
                org_id=NRCS_ORG_ID,
                registry="NP_SWC",
                identifier=None,
                url=None,
                status=None,
                verification="unverified",
                note="SWC register unreachable during this research session.",
                gap_reason="source_unreachable",
                content_hash=_hash(),
            )
        )
        session.add(
            OrgWarning(
                org_id=WORLD_VISION_ORG_ID,
                type="media_report",
                source_url="https://example.org/warning",
                occurred_on=date(2026, 7, 1),
                note="A local news report questioned World Vision Nepal's flood-response coordination.",
                retrieved_at=date(2026, 8, 18),
                content_hash=_hash(),
            )
        )

        report_nrcs = Report(
            url="https://reliefweb.int/report/nrcs-update-1",
            title="Nepal Red Cross Society flood update",
            format="Situation Report",
            published_at=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
            disaster_glide_id=DISASTER_GLIDE_ID,
            body_text="Internal-only body text: the Nepal Red Cross Society distributed 500 tarpaulins in Rasuwa.",
            body_sha256=_hash(),
        )
        report_wv = Report(
            url="https://reliefweb.int/report/world-vision-update-1",
            title="World Vision Nepal pledge",
            published_at=datetime(2026, 8, 18, 9, 0, tzinfo=UTC),
            disaster_glide_id=DISASTER_GLIDE_ID,
            body_text="Internal-only body text: World Vision Nepal pledged CHF 1,000,000 for flood response.",
            body_sha256=_hash(),
        )
        report_unicef = Report(
            url="https://reliefweb.int/report/unicef-update-1",
            title="UNICEF Nepal flood response",
            published_at=datetime(2026, 8, 17, 9, 0, tzinfo=UTC),
            disaster_glide_id=DISASTER_GLIDE_ID,
            body_text="Internal-only body text: UNICEF provided water purification kits. No rescue claim here.",
            body_sha256=_hash(),
        )
        report_local = Report(
            url="https://reliefweb.int/report/local-update-1",
            title="Local response roundup",
            published_at=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
            disaster_glide_id=DISASTER_GLIDE_ID,
            body_text="Internal-only body text: a local youth club in Timure distributed drinking water.",
            body_sha256=_hash(),
        )
        session.add_all([report_nrcs, report_wv, report_unicef, report_local])
        await session.flush()

        session.add_all(
            [
                ReportSource(report_id=report_nrcs.id, publisher="Nepal Red Cross Society"),
                ReportSource(report_id=report_wv.id, publisher="World Vision International"),
                ReportSource(report_id=report_unicef.id, publisher="UNICEF"),
                ReportSource(report_id=report_local.id, publisher="Local Media"),
            ]
        )

        statement_nrcs = ResponseStatement(
            report_id=report_nrcs.id,
            org_id=NRCS_ORG_ID,
            org_name_raw="Nepal Red Cross Society",
            activity="distributed 500 tarpaulins in Rasuwa",
            activity_type="relief_distribution",
            where_raw=["Rasuwa"],
            happened_on=date(2026, 8, 19),
            quote="distributed 500 tarpaulins",
            verification="third_party_reported",
            model="claude-sonnet-5",
            prompt_version="v2",
            status="auto",
            content_hash=_hash(),
        )
        statement_wv = ResponseStatement(
            report_id=report_wv.id,
            org_id=WORLD_VISION_ORG_ID,
            org_name_raw="World Vision Nepal",
            activity="pledged CHF 1,000,000 for flood response",
            activity_type="funding_pledged",
            where_raw=["Nuwakot"],
            happened_on=date(2026, 8, 17),
            amount=1_000_000,
            currency="CHF",
            amount_basis="pledged",
            quote="pledged CHF 1,000,000 for flood response",
            verification="third_party_reported",
            model="claude-sonnet-5",
            prompt_version="v2",
            status="auto",
            content_hash=_hash(),
        )
        statement_unicef_ok = ResponseStatement(
            report_id=report_unicef.id,
            org_id=UNICEF_ORG_ID,
            org_name_raw="UNICEF Nepal",
            activity="provided emergency water purification kits",
            activity_type="wash",
            where_raw=[],
            happened_on=date(2026, 8, 16),
            quote="provided emergency water purification kits",
            verification="third_party_reported",
            model="claude-sonnet-5",
            prompt_version="v2",
            status="auto",
            content_hash=_hash(),
        )
        # Must never reach any API response: rejected by the verbatim gate before it could.
        statement_unicef_rejected = ResponseStatement(
            report_id=report_unicef.id,
            org_id=UNICEF_ORG_ID,
            org_name_raw="UNICEF Nepal",
            activity="rescued 4000 people",
            activity_type="search_and_rescue",
            where_raw=[],
            quote="we rescued 4000 people",
            verification="third_party_reported",
            model="claude-sonnet-5",
            prompt_version="v2",
            status="rejected_unverbatim",
            content_hash=_hash(),
        )
        # Named but not identified: org_id stays null and the statement stays visible.
        statement_unmatched = ResponseStatement(
            report_id=report_local.id,
            org_id=None,
            org_name_raw=UNMATCHED_RAW_NAME,
            activity="distributed drinking water",
            activity_type="wash",
            where_raw=["Timure"],
            happened_on=date(2026, 8, 15),
            quote="distributed drinking water in Timure",
            verification="third_party_reported",
            model="claude-sonnet-5",
            prompt_version="v2",
            status="auto",
            content_hash=_hash(),
        )
        # Schema v0.3: one of the 44 hand-researched responses with no quotable sentence - the
        # fact came from a structured registration page, not a sentence an LLM could extract.
        # quote stays null; the CHECK only allows that when model = 'hand_research'. The board and
        # the statement stream both have to render this, not filter it out - it is a real, sourced
        # response, and dropping it would lose exactly the evidence the board exists to show.
        statement_nrcs_hand_research = ResponseStatement(
            report_id=report_nrcs.id,
            org_id=NRCS_ORG_ID,
            org_name_raw="Nepal Red Cross Society",
            activity="registered as WFP's implementing partner for the Rasuwa cash programme",
            activity_type="cash_assistance",
            where_raw=["Rasuwa"],
            happened_on=date(2026, 8, 21),
            quote=None,
            verification="third_party_reported",
            model="hand_research",
            prompt_version="n/a",
            status="approved",
            content_hash=_hash(),
        )
        session.add_all(
            [
                statement_nrcs,
                statement_wv,
                statement_unicef_ok,
                statement_unicef_rejected,
                statement_unmatched,
                statement_nrcs_hand_research,
            ]
        )
        await session.flush()

        session.add_all(
            [
                StatementDistrict(statement_id=statement_nrcs.id, district_code="NP0329", resolution="stated"),
                StatementDistrict(statement_id=statement_wv.id, district_code="NP0328", resolution="stated"),
                # UNICEF's statement names no place; it inherits the report's district context.
                StatementDistrict(
                    statement_id=statement_unicef_ok.id, district_code="NP0329", resolution="inherited_from_report"
                ),
                StatementDistrict(
                    statement_id=statement_nrcs_hand_research.id, district_code="NP0329", resolution="stated"
                ),
                StatementDistrict(statement_id=statement_unmatched.id, district_code="NP0329", resolution="stated"),
            ]
        )

        now = datetime.now(UTC)
        session.add_all(
            [
                IngestionRun(
                    job="seed_reference", status="succeeded", started_at=now, finished_at=now, rows_written=84
                ),
                IngestionRun(job="ingest_orgs", status="succeeded", started_at=now, finished_at=now, rows_written=420),
            ]
        )

        await session.commit()


@pytest.fixture(scope="session")
def seeded_db_url() -> Iterator[str]:
    """A freshly migrated, freshly seeded database, dropped again afterwards.

    Seeded directly through the models - as packages/core/tests/test_models.py does - rather than
    through the pipeline jobs, so these tests do not depend on WP-A or WP-B having landed yet.
    """
    maintenance = _psycopg_url(base_sync_url(), "postgres")
    with psycopg.connect(maintenance, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{SEED_DB}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{SEED_DB}"')

    sync_url = _psycopg_url(base_sync_url(), SEED_DB).replace("postgresql://", "postgresql+psycopg://", 1)
    command.upgrade(_alembic_config(sync_url), "head")
    async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)

    async def _seed_and_dispose() -> None:
        # One asyncio.run() call, not two: an asyncpg engine's connections are bound to the loop
        # that created them, so disposing it from a second, separate asyncio.run() loop would
        # either hang or raise. Seeding and disposal happen inside the same loop instead.
        engine = make_engine(async_url)
        try:
            await _seed(make_sessionmaker(engine))
        finally:
            await engine.dispose()

    asyncio.run(_seed_and_dispose())

    yield async_url
    with psycopg.connect(maintenance, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{SEED_DB}" WITH (FORCE)')


@pytest.fixture(scope="session")
async def seeded_app(seeded_db_url: str) -> AsyncIterator:
    """The app instance behind `client`, exposed on its own so a test can reach app.state.engine -
    the query-count budget test attaches an SQLAlchemy event listener to it."""
    app = create_app(database_url=seeded_db_url)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture(scope="session")
async def client(seeded_app) -> AsyncIterator[AsyncClient]:
    """A client against the seeded, migrated database. Shared read-only by every contract test."""
    async with AsyncClient(transport=ASGITransport(app=seeded_app), base_url="http://test") as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """app.deps.limiter is a module-level singleton, so its in-memory storage otherwise persists
    for the life of the test process - shared by every create_app() call and every test file, not
    scoped per app instance. Without this, a test earlier in the session that happens to hit a
    rate-limited route consumes budget a later, unrelated test then silently inherits, turning an
    expected 401 into a spurious 429. Reset before every test closes that hole."""
    from app.deps import limiter

    limiter.reset()
