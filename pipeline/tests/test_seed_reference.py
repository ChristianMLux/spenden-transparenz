"""seed_reference and the run contract every other job inherits.

The contract: a job opens an ingestion_run, upserts on natural keys, never deletes, closes the run
even when it raises, and writes zero rows on a second identical run.
"""

from __future__ import annotations

import pytest
from core.models import District, DistrictAlias, IngestionRun, Source
from core.normalise import alias_norm
from sqlalchemy import func, select

from pipeline.jobs.seed_reference import UNRESOLVABLE, seed_reference
from pipeline.migrations.add_gap_reason import load_orgs
from pipeline.runs import run_context

# 77 district names + 77 "<name> district" forms + 6 settlement variants, no collisions.
EXPECTED_ALIASES = 160


async def _count(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


async def _latest_run(session) -> IngestionRun:
    return await session.scalar(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1))


# --- the run contract --------------------------------------------------------------------------


async def test_a_successful_job_closes_its_run(job_sessionmaker, session):
    async with run_context(job_sessionmaker, "noop") as run:
        run.count(written=3)
    row = await _latest_run(session)
    assert row.job == "noop"
    assert row.status == "succeeded"
    assert row.finished_at is not None
    assert row.rows_written == 3


async def test_a_failing_job_closes_its_run_as_failed(job_sessionmaker, session):
    with pytest.raises(RuntimeError, match="boom"):
        async with run_context(job_sessionmaker, "explodes"):
            raise RuntimeError("boom")
    row = await _latest_run(session)
    assert row.status == "failed"
    assert row.finished_at is not None
    assert "boom" in row.error


async def test_a_run_records_the_git_sha(job_sessionmaker, session):
    async with run_context(job_sessionmaker, "noop"):
        pass
    row = await _latest_run(session)
    assert row.git_sha and len(row.git_sha) >= 7


async def test_a_run_never_stays_in_running(job_sessionmaker, session):
    async with run_context(job_sessionmaker, "noop"):
        pass
    with pytest.raises(RuntimeError):
        async with run_context(job_sessionmaker, "noop"):
            raise RuntimeError("x")
    still_running = await session.scalar(
        select(func.count()).select_from(IngestionRun).where(IngestionRun.status == "running")
    )
    assert still_running == 0


# --- seed_reference ----------------------------------------------------------------------------


async def test_seed_reference_loads_all_77_districts(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    assert await _count(session, District) == 77


async def test_rasuwa_resolves_to_the_code_the_api_filters_on(job_sessionmaker, session):
    """Rasuwa is NP0329, not NP0301. The spec used NP0301 as its example and the gate command;
    that code does not exist in the COD. Bagmati runs NP0320..NP0335, because the admin2 codes
    are one continuous national sequence, not a per-province one starting at 01."""
    await seed_reference(job_sessionmaker)
    district = await session.get(District, "NP0329")
    assert district.name == "Rasuwa"
    assert district.admin1_name == "Bagmati"


async def test_every_district_code_matches_the_api_pattern(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    codes = (await session.execute(select(District.code))).scalars().all()
    assert all(code.startswith("NP") and len(code) == 6 and code[2:].isdigit() for code in codes)


async def test_seed_reference_loads_the_source_catalogue(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    reliefweb = await session.get(Source, "reliefweb")
    assert reliefweb.default_verification == "third_party_reported"
    assert reliefweb.url.startswith("https://reliefweb.int")


async def test_every_source_either_states_a_licence_or_says_why_not(job_sessionmaker, session):
    """A guessed licence is exactly the kind of claim this product exists not to make."""
    await seed_reference(job_sessionmaker)
    sources = (await session.execute(select(Source))).scalars().all()
    assert len(sources) >= 10
    for source in sources:
        assert source.licence is not None or (source.licence_note or "").strip(), source.id


# --- district aliases -------------------------------------------------------------------------


async def test_every_district_name_is_an_alias(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    rasuwa = await session.get(DistrictAlias, "rasuwa")
    assert rasuwa.district_code == "NP0329"


async def test_the_district_suffix_form_resolves(job_sessionmaker, session):
    """The extraction output says "Rasuwa district" as often as "Rasuwa"."""
    await seed_reference(job_sessionmaker)
    assert (await session.get(DistrictAlias, "rasuwa district")).district_code == "NP0329"


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("timure", "NP0329"),
        ("syabrubesi", "NP0329"),
        ("rasuwagadhi", "NP0329"),
        ("nuwakot district", "NP0328"),
        ("dhading district", "NP0330"),
        ("chitwan", "NP0335"),
        ("chitwan district", "NP0335"),
        ("chitwan district mugling", "NP0335"),
        ("gorkha district", "NP0436"),
        ("kavrepalanchok", "NP0324"),
    ],
)
async def test_the_settlement_aliases_the_pilot_data_needs(job_sessionmaker, session, alias, expected):
    await seed_reference(job_sessionmaker)
    row = await session.get(DistrictAlias, alias)
    assert row is not None, f"{alias} does not resolve"
    assert row.district_code == expected


@pytest.mark.parametrize(
    "phrase",
    [
        "unspecified",
        "unspecified (remote flood-affected areas)",
        "Nepal",
        "northern Nepal",
        "along Bhote Koshi and Trishuli rivers",
        "along the Bhotekoshi and Trishuli rivers",
    ],
)
async def test_these_phrases_must_resolve_to_no_district(job_sessionmaker, session, phrase):
    """A river corridor crosses districts and "Nepal" is the whole country. Guessing a district
    here would invent a location, so the statement keeps where_raw and gets no district row."""
    await seed_reference(job_sessionmaker)
    assert await session.get(DistrictAlias, alias_norm(phrase)) is None


async def test_every_where_raw_value_in_the_pilot_data_is_accounted_for(job_sessionmaker, session):
    """Either it resolves to a district, or it is on the deliberate unresolvable list. Nothing may
    silently fall through, because a silent miss looks the same as "no response in that district"."""
    await seed_reference(job_sessionmaker)
    unaccounted = []
    for org in load_orgs():
        for response in org["current_response"]:
            for raw in response.get("where") or []:
                norm = alias_norm(raw)
                resolved = await session.get(DistrictAlias, norm) is not None
                if not resolved and norm not in {alias_norm(p) for p in UNRESOLVABLE}:
                    unaccounted.append(raw)
    assert unaccounted == [], f"where_raw values with no decision: {sorted(set(unaccounted))}"


async def test_the_second_run_writes_zero_rows(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    first = await _latest_run(session)
    assert first.rows_written == 77 + 10 + EXPECTED_ALIASES

    await seed_reference(job_sessionmaker)
    second = await _latest_run(session)
    assert second.status == "succeeded"
    assert second.rows_written == 0
    assert second.rows_skipped == 77 + 10 + EXPECTED_ALIASES


async def test_the_second_run_deletes_nothing(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    await seed_reference(job_sessionmaker)
    assert await _count(session, District) == 77
    assert await _count(session, Source) >= 10


async def test_a_changed_district_name_is_updated_not_duplicated(job_sessionmaker, session):
    await seed_reference(job_sessionmaker)
    async with job_sessionmaker() as write:
        district = await write.get(District, "NP0329")
        district.name = "Stale Name"
        await write.commit()

    await seed_reference(job_sessionmaker)
    assert await _count(session, District) == 77
    refreshed = await session.get(District, "NP0329")
    await session.refresh(refreshed)
    assert refreshed.name == "Rasuwa"
