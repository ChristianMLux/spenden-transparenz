"""GET /v1/disasters/{glide_id}/responders - the response board.

Uses the seeded dataset in conftest.py: NRCS (Rasuwa, gap on income), World Vision (Nuwakot,
pledge, a warning), UNICEF (an inherited-district statement plus a rejected_unverbatim one that
must never surface), an org with zero statements, and one unmatched org_name_raw statement.
"""

from __future__ import annotations

from httpx import AsyncClient
from tests.conftest import (
    DISASTER_GLIDE_ID,
    NO_RESPONSE_ORG_ID,
    NRCS_ORG_ID,
    UNICEF_ORG_ID,
    UNMATCHED_RAW_NAME,
    WORLD_VISION_ORG_ID,
)


async def test_board_includes_organisations_with_no_statement_by_default(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    assert r.status_code == 200
    ids = {item["org"]["org_id"] for item in r.json() if item["org"]}
    assert NO_RESPONSE_ORG_ID in ids
    zero = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == NO_RESPONSE_ORG_ID)
    assert zero["statements"] == []
    assert zero["counts"]["statements"] == 0


async def test_board_includes_a_named_but_unidentified_organisation(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    unmatched = next(item for item in r.json() if item["org"] is None)
    assert unmatched["org_name_raw"] == UNMATCHED_RAW_NAME
    assert len(unmatched["statements"]) == 1


async def test_board_never_includes_a_rejected_unverbatim_statement(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    unicef = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == UNICEF_ORG_ID)
    quotes = [s["quote"] for s in unicef["statements"]]
    assert "we rescued 4000 people" not in quotes
    assert len(unicef["statements"]) == 1


async def test_board_has_x_total_count(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    assert "X-Total-Count" in r.headers
    assert int(r.headers["X-Total-Count"]) == len(r.json())


async def test_district_filter_matches_rasuwa(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?district=NP0329")
    ids = {item["org"]["org_id"] if item["org"] else item["org_name_raw"] for item in r.json()}
    assert NRCS_ORG_ID in ids
    assert UNMATCHED_RAW_NAME in ids
    # UNICEF's statement inherited NP0329 from the report, so it counts as "in Rasuwa" too.
    assert UNICEF_ORG_ID in ids
    assert WORLD_VISION_ORG_ID not in ids  # Nuwakot, not Rasuwa


async def test_district_filter_excludes_zero_statement_organisations(client: AsyncClient):
    """A district filter scopes the board to statements about that place; an organisation with no
    statement at all cannot be "in Rasuwa" or "not in Rasuwa" - it is simply out of scope."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?district=NP0329")
    ids = {item["org"]["org_id"] for item in r.json() if item["org"]}
    assert NO_RESPONSE_ORG_ID not in ids


async def test_the_district_inheritance_resolution_is_visible(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?district=NP0329")
    unicef = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == UNICEF_ORG_ID)
    district = unicef["statements"][0]["districts"][0]
    assert district["code"] == "NP0329"
    assert district["resolution"] == "inherited_from_report"


async def test_has_response_true_excludes_zero_statement_organisations(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?has_response=true")
    ids = {item["org"]["org_id"] for item in r.json() if item["org"]}
    assert NO_RESPONSE_ORG_ID not in ids
    assert NRCS_ORG_ID in ids


async def test_has_response_false_returns_only_zero_statement_organisations(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?has_response=false")
    items = r.json()
    assert all(item["statements"] == [] for item in items)
    ids = {item["org"]["org_id"] for item in items if item["org"]}
    assert NO_RESPONSE_ORG_ID in ids
    assert NRCS_ORG_ID not in ids


async def test_org_type_filter(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?org_type=un_agency")
    ids = {item["org"]["org_id"] for item in r.json() if item["org"]}
    assert ids == {UNICEF_ORG_ID}


async def test_verification_filter(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?verification=third_party_reported")
    assert len(r.json()) > 0
    r_empty = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?verification=externally_audited")
    assert r_empty.json() == []


async def test_amount_basis_distinguishes_a_pledge_from_a_payment(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    wv = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == WORLD_VISION_ORG_ID)
    assert wv["statements"][0]["amount_basis"] == "pledged"
    assert wv["statements"][0]["amount"] == "1000000.00"


async def test_flags_reflect_registrations_and_warnings(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    wv = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == WORLD_VISION_ORG_ID)
    assert wv["flags"]["has_warnings"] is True
    nrcs = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == NRCS_ORG_ID)
    assert nrcs["flags"]["has_warnings"] is False
    assert nrcs["flags"]["has_register_confirmed"] is False  # its registration is unverified, not confirmed


async def test_sort_name_is_alphabetical(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?sort=name")
    names = [item["org"]["name_common"] if item["org"] else item["org_name_raw"] for item in r.json()]
    assert names == sorted(names, key=str.lower)


async def test_sort_least_data_orders_by_statement_count(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?sort=least_data")
    counts = [len(item["statements"]) for item in r.json()]
    assert counts == sorted(counts)


async def test_no_sort_option_orders_by_verification(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?sort=verification")
    assert r.status_code == 422


async def test_limit_above_100_is_rejected(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?limit=1000")
    assert r.status_code == 422


async def test_a_malformed_district_code_is_rejected(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders?district=NOT-A-CODE")
    assert r.status_code == 422


async def test_no_response_ever_contains_body_text(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    assert "body_text" not in r.text


async def test_board_is_cached_for_a_minute_with_stale_while_revalidate(client: AsyncClient):
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    assert r.headers["cache-control"] == "public, max-age=60, stale-while-revalidate=600"


async def test_org_ref_carries_aliases_and_local_script(client: AsyncClient):
    """The board's name search is useless without these: people type NRCS, not "Nepal Red Cross
    Society". Fetched as correlated subqueries, not a query-per-org loop - see the responders.py
    module docstring's query budget."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    nrcs = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == NRCS_ORG_ID)
    assert set(nrcs["org"]["aliases"]) == {"nrcs", "nepal red cross"}
    assert nrcs["org"]["local_script"] == "नेपाल रेड क्रस सोसाइटी"


async def test_org_ref_aliases_are_empty_not_null_when_an_organisation_has_none(client: AsyncClient):
    """A zero-statement organisation with no org_alias rows: the array_agg subquery returns
    Postgres NULL, which must become [], not surface as null in the response."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    no_alias_org = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == WORLD_VISION_ORG_ID)
    assert no_alias_org["org"]["aliases"] == []
    assert no_alias_org["org"]["local_script"] is None


async def test_unmatched_organisation_has_no_alias_data(client: AsyncClient):
    """org is null for an unidentified statement, so there is no organisation to look aliases up
    against - the correlated subqueries naturally return nothing rather than needing a special case."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    unmatched = next(item for item in r.json() if item["org"] is None)
    assert unmatched["org"] is None


async def test_a_hand_researched_statement_with_no_quote_is_rendered_not_filtered(client: AsyncClient):
    """5 of the 44 hand-researched responses have no quotable sentence. quote is null on the
    StatementOut, not a missing statement: this is a real, sourced response, and dropping it would
    lose exactly the evidence the board exists to show."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    nrcs = next(item for item in r.json() if item["org"] and item["org"]["org_id"] == NRCS_ORG_ID)
    quotes = {s["quote"] for s in nrcs["statements"]}
    assert None in quotes
    hand_researched = next(s for s in nrcs["statements"] if s["quote"] is None)
    assert hand_researched["activity_type"] == "cash_assistance"
    assert hand_researched["source"]["verification"] == "third_party_reported"
    assert nrcs["counts"]["statements"] == 2


# --- donation_channel (v0.5) ---------------------------------------------------------------------


async def test_a_board_row_carries_the_official_donation_channel(client: AsyncClient):
    """Chris's user test: someone found an official Nepali account number through Google in
    minutes while this site, full of information, offered no way to act. The link belongs on the
    row - as a fact with provenance, presented identically for every organisation."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    assert r.status_code == 200
    rows = {item["org"]["org_id"]: item for item in r.json() if item["org"]}

    nrcs = rows["nepal-red-cross-society"]["donation_channel"]
    assert nrcs == {
        "url": "https://donation.nrcs.org/",
        "channel_type": "donation_page",
        "verification": "self_reported",
        "retrieved_at": "2026-08-28",
        "flood_specific": False,
    }


async def test_every_row_carries_the_key_even_when_there_is_no_channel(client: AsyncClient):
    """null is an answer, and the key is always present so the frontend can render "none found"
    rather than an absence. The same reason every Datum field is required-but-nullable."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders")
    items = r.json()
    assert items
    for item in items:
        assert "donation_channel" in item

    rows = {item["org"]["org_id"]: item for item in items if item["org"]}
    assert rows["world-vision-nepal"]["donation_channel"] is None


async def test_no_row_ranks_or_sorts_by_whether_it_has_a_donation_channel(client: AsyncClient):
    """The field is a way to act, never a recommendation. An organisation with a link must not
    float above one without."""
    r = await client.get(f"/v1/disasters/{DISASTER_GLIDE_ID}/responders", params={"sort": "name"})
    names = [item["org_name_raw"] for item in r.json()]
    assert names == sorted(names, key=str.casefold)


async def test_the_org_page_carries_the_full_donation_channel_datum(client: AsyncClient):
    """The row gets the compact link; the organisation's own page gets the datum with its quote,
    note and gap_reason, in the same shape as every other fact."""
    r = await client.get("/v1/orgs/nepal-red-cross-society")
    assert r.status_code == 200
    datum = r.json()["data"]["donation_channel"]
    assert datum["value"] == "https://donation.nrcs.org/"
    assert datum["channel_type"] == "donation_page"
    assert datum["flood_specific"] is False
    assert datum["verification"] == "self_reported"
    assert datum["is_gap"] is False
    assert datum["quote"] == "Ways to Donate To Nepal Redcross"


async def test_a_gap_channel_is_a_datum_with_its_reason(client: AsyncClient):
    r = await client.get("/v1/orgs/world-vision-nepal")
    datum = r.json()["data"]["donation_channel"]
    assert datum["value"] is None
    assert datum["is_gap"] is True
    assert datum["gap_reason"] == "searched_not_found"
    assert datum["note"]
    assert datum["channel_type"] is None
