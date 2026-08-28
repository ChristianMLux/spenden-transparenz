"""The contract the web team generates its types from.

The stub is about types, not data: every route exists with its final path, its final query
parameters and its final response model, and the handler returns an empty but schema-valid
payload. WP-C fills the bodies in without changing the shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.main import create_app

API_DIR = Path(__file__).resolve().parents[1]
SPEC = create_app().openapi()

EXPECTED_PATHS = {
    "/health",
    "/health/ready",
    "/v1/disasters",
    "/v1/disasters/{glide_id}",
    "/v1/disasters/{glide_id}/responders",
    "/v1/orgs",
    "/v1/orgs/{org_id}",
    "/v1/orgs/{org_id}/history",
    "/v1/statements",
    "/v1/meta/districts",
    "/v1/meta/sources",
    "/v1/meta/enums",
    "/v1/meta/freshness",
    "/v1/admin/ingest/{job}",
    "/v1/admin/runs",
}


def test_every_spec_route_exists():
    missing = EXPECTED_PATHS - set(SPEC["paths"])
    assert missing == set(), f"missing routes: {sorted(missing)}"


def test_the_committed_openapi_json_matches_the_app():
    """The web team generates lib/types.ts from the committed file. If this fails, run
    `python apps/api/scripts/export_openapi.py` and commit the result."""
    committed = json.loads((API_DIR / "openapi.json").read_text(encoding="utf-8"))
    assert SPEC == committed


def test_no_response_model_can_serialise_body_text():
    """report.body_text is third-party copyright. It is stored for extraction and never served."""
    assert "body_text" not in json.dumps(SPEC)


def test_the_datum_schema_keeps_every_key_for_a_gap():
    """A gap is {value: null, is_gap: true, note, gap_reason} - the key never disappears, because
    a missing key and a null value read completely differently in a frontend."""
    properties = SPEC["components"]["schemas"]["Datum"]["properties"]
    assert {"value", "is_gap", "note", "gap_reason", "source_url", "retrieved_at", "verification"} <= set(properties)


def test_nothing_in_the_contract_offers_a_score_or_a_rating():
    blob = json.dumps(SPEC).lower()
    for word in ('"score"', '"rating"', '"rank"', '"grade"', '"tier"'):
        assert word not in blob, f"the contract exposes {word}"


def test_sorting_by_verification_is_not_offered():
    """Sorting by verification would rank organisations by how deeply we researched them."""
    for path in ("/v1/disasters/{glide_id}/responders", "/v1/orgs", "/v1/statements"):
        for parameter in SPEC["paths"][path]["get"].get("parameters", []):
            if parameter["name"] == "sort":
                allowed = parameter["schema"].get("enum") or parameter["schema"].get("default")
                assert "verification" not in json.dumps(allowed)


def test_the_district_pattern_sits_on_the_item_not_on_the_list():
    """Query(pattern=...) on a list[str] constrains the array, not its items: FastAPI drops the
    pattern from the schema and pydantic raises at request time, so codes arrive unvalidated."""
    parameters = {p["name"]: p for p in SPEC["paths"]["/v1/disasters/{glide_id}/responders"]["get"]["parameters"]}
    schema = parameters["district"]["schema"]
    assert schema["type"] == "array"
    assert schema["items"]["pattern"] == r"^NP\d{4}$"


async def test_a_malformed_district_code_is_rejected(client_no_db):
    """The assertion that matters: not that the schema claims a pattern, but that a bad code is
    actually refused before it can reach a query."""
    response = await client_no_db.get("/v1/disasters/ff-2026-000162-npl/responders?district=NP1")
    assert response.status_code == 422
    response = await client_no_db.get("/v1/disasters/ff-2026-000162-npl/responders?district=NP0329' OR 1=1--")
    assert response.status_code == 422


async def test_a_valid_district_code_is_accepted(client_no_db):
    response = await client_no_db.get("/v1/disasters/ff-2026-000162-npl/responders?district=NP0329")
    assert response.status_code == 200


def test_limit_is_capped_at_100():
    parameters = {p["name"]: p for p in SPEC["paths"]["/v1/orgs"]["get"]["parameters"]}
    assert json.dumps(parameters["limit"]).count("100") >= 1


@pytest.mark.parametrize(
    "path",
    [
        "/v1/disasters",
        "/v1/orgs",
        "/v1/statements",
        "/v1/meta/districts",
        "/v1/meta/sources",
        "/v1/meta/enums",
        "/v1/meta/freshness",
    ],
)
async def test_stub_routes_answer_with_a_schema_valid_payload(client_no_db, path):
    response = await client_no_db.get(path)
    assert response.status_code == 200, response.text
    assert response.headers["x-stub"] == "true"
    response.json()


async def test_the_stub_marks_itself_so_nobody_ships_it_by_accident(client_no_db):
    response = await client_no_db.get("/v1/orgs")
    assert response.headers["x-stub"] == "true"


async def test_admin_ingest_requires_a_token_even_in_the_stub(client_no_db):
    """The stub must not be the one build where the ingestion trigger is open."""
    assert (await client_no_db.post("/v1/admin/ingest/seed_reference")).status_code == 401
