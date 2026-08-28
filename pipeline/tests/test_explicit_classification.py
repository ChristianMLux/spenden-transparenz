"""Classification is data a person wrote, not a keyword match.

The derivation this replaces got 14 of 44 wrong. Three of those invented a financial claim from a
sentence containing no money at all, and `amount_basis` is rendered next to the figure on the
board - so "disbursed" on a statement with no amount is the product asserting a payment nobody
reported.
"""

from __future__ import annotations

import json
from pathlib import Path

from core import enums

from pipeline.migrations.add_gap_reason import load_orgs
from pipeline.migrations.explicit_classification import CLASSIFICATION, apply, classify

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "schema" / "org.schema.json").read_text(encoding="utf-8"))


def test_the_schema_allows_both_fields():
    props = SCHEMA["properties"]["current_response"]["items"]["properties"]
    assert props["activity_type"]["$ref"] == "#/$defs/activity_type"
    assert props["amount_basis"]["$ref"] == "#/$defs/amount_basis"


def test_neither_field_is_required():
    """A record that does not state one is not invalid; the loader falls back to a value that
    claims nothing."""
    required = SCHEMA["properties"]["current_response"]["items"]["required"]
    assert "activity_type" not in required
    assert "amount_basis" not in required


def test_every_researched_response_states_its_classification():
    missing = [
        (org["org_id"], index)
        for org in load_orgs()
        for index, response in enumerate(org["current_response"])
        if not response.get("activity_type") or not response.get("amount_basis")
    ]
    assert missing == [], f"responses with no explicit classification: {missing}"


def test_every_written_value_is_a_legal_enum_member():
    for org in load_orgs():
        for response in org["current_response"]:
            assert response["activity_type"] in enums.ACTIVITY_TYPE, org["org_id"]
            assert response["amount_basis"] in enums.AMOUNT_BASIS, org["org_id"]


def test_a_statement_with_no_amount_never_claims_money_moved():
    """The failure that made this migration necessary. pledged, released and disbursed are claims
    about money; a sentence with no figure cannot support one. appeal is the single exception -
    an appeal is a request, and it can be launched without naming a target."""
    financial = {"pledged", "released", "disbursed", "raised"}
    offenders = [
        (org["org_id"], response["what"][:60])
        for org in load_orgs()
        for response in org["current_response"]
        if response.get("amount") is None and response["amount_basis"] in financial
    ]
    assert offenders == [], f"money claimed with no amount: {offenders}"


def test_the_three_corrections_that_invented_a_payment():
    """Regression: each of these had a financial amount_basis on a sentence with no money in it."""
    assert classify("plan-international-nepal", 0) == ("presence_declared", "reported")
    assert classify("wfp-nepal", 0) == ("relief_distribution", "reported")
    assert classify("the-rising-youth-club", 0) == ("presence_declared", "reported")


def test_paused_activities_are_not_an_appeal():
    """malteser-international's sentence says its activities are temporarily paused for safety.
    The derivation read it as a launched appeal."""
    assert classify("malteser-international", 0) == ("presence_declared", "reported")


def test_coordination_is_its_own_activity():
    """Two records describe coordinating with authorities or partners, which is neither logistics
    nor a shrug at 'other'."""
    assert classify("mercy-corps", 0)[0] == "coordination"
    assert classify("community-self-reliance-centre", 0)[0] == "coordination"
    assert "coordination" in enums.ACTIVITY_TYPE


def test_applying_twice_changes_nothing():
    org = {
        "org_id": "mercy-corps",
        "current_response": [{"what": "coordinating with authorities", "activity_type": None, "amount_basis": None}],
    }
    assert apply(org) == 2
    assert apply(org) == 0


def test_an_unknown_record_is_left_alone_rather_than_guessed():
    org = {"org_id": "not-in-the-table", "current_response": [{"what": "something"}]}
    assert apply(org) == 0
    assert "activity_type" not in org["current_response"][0]


def test_the_table_covers_every_response_and_nothing_else():
    actual = {(org["org_id"], index) for org in load_orgs() for index, _ in enumerate(org["current_response"])}
    assert set(CLASSIFICATION) == actual
