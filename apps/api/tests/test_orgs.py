"""GET /v1/orgs, GET /v1/orgs/{org_id}, GET /v1/orgs/{org_id}/history."""

from __future__ import annotations

from httpx import AsyncClient
from tests.conftest import NO_RESPONSE_ORG_ID, NRCS_ORG_ID, WORLD_VISION_ORG_ID


async def test_list_orgs_includes_the_seeded_organisations(client: AsyncClient):
    r = await client.get("/v1/orgs")
    assert r.status_code == 200
    ids = {o["org_id"] for o in r.json()}
    assert {NRCS_ORG_ID, WORLD_VISION_ORG_ID, NO_RESPONSE_ORG_ID} <= ids
    assert "X-Total-Count" in r.headers


async def test_list_orgs_filters_by_org_type(client: AsyncClient):
    r = await client.get("/v1/orgs?org_type=un_agency")
    ids = {o["org_id"] for o in r.json()}
    assert NRCS_ORG_ID not in ids


async def test_list_orgs_filters_by_hq(client: AsyncClient):
    r = await client.get("/v1/orgs?hq=local")
    ids = {o["org_id"] for o in r.json()}
    assert NRCS_ORG_ID in ids
    assert WORLD_VISION_ORG_ID not in ids  # hq_country=US


async def test_list_orgs_name_search_is_case_insensitive(client: AsyncClient):
    r = await client.get("/v1/orgs?q=RED CROSS")
    ids = {o["org_id"] for o in r.json()}
    assert NRCS_ORG_ID in ids


async def test_get_org_returns_every_datum_gaps_included(client: AsyncClient):
    r = await client.get(f"/v1/orgs/{NRCS_ORG_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["org_id"] == NRCS_ORG_ID
    assert "financial_transparency.income" in body["data"]
    income = body["data"]["financial_transparency.income"]
    assert income["value"] is None
    assert income["is_gap"] is True
    assert income["gap_reason"] == "source_unreachable"
    assert income["note"]
    assert "financial_transparency.income" in body["data_gaps"]

    value = body["data"]["names.common"]
    assert value["value"] == "Nepal Red Cross Society"
    assert value["is_gap"] is False
    assert value["gap_reason"] is None
    assert value["source_url"]


async def test_get_org_datum_keys_never_differ_between_a_gap_and_a_value(client: AsyncClient):
    body = (await client.get(f"/v1/orgs/{NRCS_ORG_ID}")).json()
    assert body["data"]["financial_transparency.income"].keys() == body["data"]["names.common"].keys()


async def test_get_org_registration_row_stays_visible_with_a_null_identifier(client: AsyncClient):
    body = (await client.get(f"/v1/orgs/{NRCS_ORG_ID}")).json()
    swc = next(reg for reg in body["registrations"] if reg["registry"] == "NP_SWC")
    assert swc["identifier"] is None
    assert swc["gap_reason"] == "source_unreachable"
    assert swc["note"]


async def test_get_org_includes_its_statements(client: AsyncClient):
    body = (await client.get(f"/v1/orgs/{NRCS_ORG_ID}")).json()
    assert len(body["statements"]) == 1
    assert body["statements"][0]["quote"] == "distributed 500 tarpaulins"


async def test_get_org_includes_warnings(client: AsyncClient):
    body = (await client.get(f"/v1/orgs/{WORLD_VISION_ORG_ID}")).json()
    assert len(body["warnings"]) == 1
    assert body["warnings"][0]["type"] == "media_report"


async def test_get_org_unknown_id_is_404(client: AsyncClient):
    r = await client.get("/v1/orgs/does-not-exist")
    assert r.status_code == 404


async def test_get_org_history_for_the_known_gap(client: AsyncClient):
    r = await client.get(f"/v1/orgs/{NRCS_ORG_ID}/history?path=financial_transparency.income")
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) == 1
    assert entries[0]["datum"]["is_gap"] is True
    assert entries[0]["superseded_at"] is None


async def test_get_org_history_for_an_unknown_path_is_empty(client: AsyncClient):
    r = await client.get(f"/v1/orgs/{NRCS_ORG_ID}/history?path=does.not.exist")
    assert r.json() == []


async def test_org_detail_is_cached_five_minutes(client: AsyncClient):
    r = await client.get(f"/v1/orgs/{NRCS_ORG_ID}")
    assert r.headers["cache-control"] == "public, max-age=300"
