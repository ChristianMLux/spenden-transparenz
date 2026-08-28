"""/v1/meta/districts, /v1/meta/sources, /v1/meta/enums, /v1/meta/freshness."""

from __future__ import annotations

from core import enums
from httpx import AsyncClient


async def test_districts_lists_the_seeded_districts(client: AsyncClient):
    r = await client.get("/v1/meta/districts")
    assert r.status_code == 200
    codes = {d["code"] for d in r.json()}
    assert {"NP0329", "NP0328", "NP0330"} <= codes
    rasuwa = next(d for d in r.json() if d["code"] == "NP0329")
    assert rasuwa["name"] == "Rasuwa"
    assert rasuwa["admin1_name"] == "Bagmati"


async def test_districts_is_cached_for_an_hour(client: AsyncClient):
    r = await client.get("/v1/meta/districts")
    assert r.headers["cache-control"] == "public, max-age=3600"


async def test_sources_lists_licences(client: AsyncClient):
    r = await client.get("/v1/meta/sources")
    assert r.status_code == 200
    # seed_reference has not necessarily run in this database - a real source list is not
    # guaranteed, but the shape must hold for whatever rows exist.
    for source in r.json():
        assert "licence" in source and "default_verification" in source


async def test_enums_is_served_from_core_enums(client: AsyncClient):
    r = await client.get("/v1/meta/enums")
    assert r.status_code == 200
    body = r.json()["enums"]
    assert body["gap_reason"] == list(enums.GAP_REASON)
    assert body["verification"] == list(enums.VERIFICATION)
    assert set(body) == set(enums.ALL_ENUMS)


async def test_freshness_reports_the_seeded_runs(client: AsyncClient):
    r = await client.get("/v1/meta/freshness")
    assert r.status_code == 200
    body = r.json()
    assert "generated_at" in body
    jobs = {j["job"]: j for j in body["jobs"]}
    assert jobs["seed_reference"]["rows_written"] == 84
    assert jobs["ingest_orgs"]["rows_written"] == 420
    assert jobs["seed_reference"]["last_success_at"] is not None
