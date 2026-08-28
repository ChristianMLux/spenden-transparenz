"""The product rules, checked against a running API with real data.

Everything here is the executable form of the spec's non-negotiables: a gap keeps every key,
body_text never leaves the database, admin is always 401 with no distinct "unconfigured" status,
CORS never answers with a wildcard, an ETag round-trip 304s, and the responders board does not
issue one query per organisation.
"""

from __future__ import annotations

from datetime import date

import pytest
from app.schemas import Datum, serialise_datum
from core.models import OrgDatum
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from tests.conftest import DISASTER_GLIDE_ID, NRCS_ORG_ID


def _gap_row() -> OrgDatum:
    return OrgDatum(
        org_id="x",
        path="financial_transparency.income",
        value=None,
        is_gap=True,
        note="Searched in the 2026-08-28 research pass; not found.",
        gap_reason="searched_not_found",
        verification="unverified",
    )


def _value_row() -> OrgDatum:
    return OrgDatum(
        org_id="x",
        path="names.common",
        value="Nepal Red Cross Society",
        is_gap=False,
        value_type="string",
        source_url="https://nrcs.org",
        retrieved_at=date(2026, 8, 20),
        verification="self_reported",
    )


def test_serialise_datum_keeps_the_same_keys_for_a_gap_and_a_value():
    """A missing key and a null value read completely differently in a frontend. The gap and the
    value must serialise to the exact same set of keys."""
    gap = serialise_datum(_gap_row()).model_dump()
    value = serialise_datum(_value_row()).model_dump()
    assert gap.keys() == value.keys()


def test_serialise_datum_gap_has_null_value_and_is_gap_true():
    datum = serialise_datum(_gap_row())
    assert datum.value is None
    assert datum.is_gap is True
    assert datum.note and datum.gap_reason


def test_serialise_datum_value_has_no_gap_reason():
    datum = serialise_datum(_value_row())
    assert datum.is_gap is False
    assert datum.value == "Nepal Red Cross Society"
    assert datum.gap_reason is None


def test_datum_model_dump_always_has_the_full_key_set():
    """Regression guard for the shape itself, independent of the serialiser."""
    expected = {
        "value",
        "is_gap",
        "value_type",
        "currency",
        "fiscal_year",
        "scope",
        "source_url",
        "retrieved_at",
        "quote",
        "note",
        "verification",
        "gap_reason",
    }
    assert set(Datum(is_gap=True, verification="unverified").model_dump()) == expected


# --- Task C-8: the contract tests that carry the product, run against the seeded database -----


def _walk_datum_objects(node):
    """Any dict that looks like a Datum (has is_gap and verification) plus every such dict nested
    inside lists/dicts - used to check the provenance invariant across a whole JSON response."""
    if isinstance(node, dict):
        if "is_gap" in node and "verification" in node:
            yield node
        for value in node.values():
            yield from _walk_datum_objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_datum_objects(item)


async def test_every_field_in_a_responders_response_is_sourced_or_an_explicit_gap(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?district=NP0329")
    assert r.status_code == 200
    items = r.json()
    assert items, "the district=NP0329 board must not be empty in the seeded dataset"
    for datum in _walk_datum_objects(items):
        assert datum["is_gap"] is True or datum["source_url"]


async def test_a_known_gap_is_explicit(client: AsyncClient):
    """The PO-3 gate example: nepal-red-cross-society's income has value: null, is_gap: true, and
    both a note and a gap_reason - never a bare empty cell."""
    r = await client.get(f"/v1/orgs/{NRCS_ORG_ID}")
    income = r.json()["data"]["financial_transparency.income"]
    assert income["value"] is None
    assert income["is_gap"] is True
    assert income["note"]
    assert income["gap_reason"]


ALL_GET_PATHS = [
    "/v1/disasters",
    f"/v1/disasters/{DISASTER_GLIDE_ID}",
    f"/v1/disasters/{DISASTER_GLIDE_ID}/responders",
    "/v1/orgs",
    f"/v1/orgs/{NRCS_ORG_ID}",
    f"/v1/orgs/{NRCS_ORG_ID}/history?path=financial_transparency.income",
    "/v1/statements",
    "/v1/meta/districts",
    "/v1/meta/sources",
    "/v1/meta/enums",
    "/v1/meta/freshness",
]


@pytest.mark.parametrize("path", ALL_GET_PATHS)
async def test_no_response_ever_contains_body_text(client: AsyncClient, path: str):
    r = await client.get(path)
    assert "body_text" not in r.text


async def test_limit_above_100_is_rejected(client: AsyncClient):
    assert (await client.get("/v1/orgs?limit=1000")).status_code == 422


async def test_admin_without_a_token_is_401(client: AsyncClient):
    assert (await client.post("/v1/admin/ingest/seed_reference")).status_code == 401


async def test_admin_with_a_wrong_token_is_401_and_takes_the_same_path(client: AsyncClient):
    r = await client.post("/v1/admin/ingest/seed_reference", headers={"X-Admin-Token": "wrong"})
    assert r.status_code == 401


async def test_etag_returns_304(client: AsyncClient):
    first = await client.get("/v1/meta/districts")
    assert "etag" in first.headers
    second = await client.get("/v1/meta/districts", headers={"If-None-Match": first.headers["etag"]})
    assert second.status_code == 304
    assert second.content == b""


async def test_etag_changes_if_the_body_would_differ(client: AsyncClient):
    districts = await client.get("/v1/meta/districts")
    enums = await client.get("/v1/meta/enums")
    assert districts.headers["etag"] != enums.headers["etag"]


async def test_cors_never_answers_with_a_wildcard(client: AsyncClient):
    r = await client.options(
        "/v1/orgs", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert r.headers.get("access-control-allow-origin") != "*"


async def test_no_endpoint_sorts_by_verification(client: AsyncClient):
    assert (await client.get("/v1/orgs?sort=verification")).status_code == 422
    assert (await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?sort=verification")).status_code == 422


# --- the performance rule for the board: the responders board is not one query per organisation


async def _count_queries(seeded_app, path: str) -> tuple[int, list[str]]:
    """Attach an SQLAlchemy event listener around exactly one request and count the SQL statements
    it emits. A fresh client, not the shared session-scoped `client` fixture, so the count reflects
    only this one request and not whatever earlier tests also did against the shared connection."""
    engine = seeded_app.state.engine
    statements: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", _record)
    try:
        async with AsyncClient(transport=ASGITransport(app=seeded_app), base_url="http://test") as isolated:
            response = await isolated.get(path)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _record)
    assert response.status_code == 200, response.text
    return len(statements), statements


async def test_the_full_responders_board_issues_at_most_four_queries(seeded_app):
    count, statements = await _count_queries(seeded_app, f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    assert count <= 4, f"responders board issued {count} queries: {statements}"


async def test_the_gate_command_district_filtered_board_issues_at_most_four_queries(seeded_app):
    """The exact PO-3 gate command: GET /v1/disasters/{glide_id}/responders?district=NP0329."""
    count, statements = await _count_queries(
        seeded_app, f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?district=NP0329"
    )
    assert count <= 4, f"district-filtered board issued {count} queries: {statements}"
