"""nepal_presence.mode must be able to say "we do not know".

The seven records this fixes were not a data-entry mistake. They were researchers recording a gap
in the only vocabulary the schema offered, because datum_presence_mode was the one datum type with
no null in its value enum.
"""

from __future__ import annotations

import json
from pathlib import Path

from core import enums

from pipeline.migrations.add_gap_reason import load_orgs, walk_datums
from pipeline.migrations.nullable_presence_mode import convert, is_unsourced_unknown

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "schema" / "org.schema.json").read_text(encoding="utf-8"))

GAP_REASON = ("not_searched", "searched_not_found", "source_unreachable", "not_public")


def test_the_schema_now_lets_a_presence_mode_be_null():
    value = SCHEMA["$defs"]["datum_presence_mode"]["allOf"][1]["properties"]["value"]
    assert None in value["enum"]
    assert "null" in value["type"]


def test_unknown_stays_a_legal_value():
    """A source that says the mode is unclear is a different, sourced claim. It must stay
    expressible - this migration is about the unsourced case only."""
    value = SCHEMA["$defs"]["datum_presence_mode"]["allOf"][1]["properties"]["value"]
    assert "unknown" in value["enum"]
    assert "unknown" in enums.PRESENCE_MODE


def test_a_sourced_unknown_is_not_touched():
    org = {
        "data_gaps": [],
        "nepal_presence": {
            "mode": {
                "value": "unknown",
                "source_url": "https://example.org/about",
                "retrieved_at": "2026-08-28",
                "verification": "self_reported",
                "quote": "our role in Nepal is under review",
            }
        },
    }
    assert convert(org) == 0
    assert org["nepal_presence"]["mode"]["value"] == "unknown"


def test_an_unsourced_unknown_becomes_a_gap():
    org = {
        "data_gaps": ["nepal_presence.mode"],
        "nepal_presence": {
            "mode": {"value": "unknown", "source_url": None, "retrieved_at": "2026-08-28", "verification": "unverified"}
        },
    }
    assert convert(org) > 0
    datum = org["nepal_presence"]["mode"]
    assert datum["value"] is None
    assert datum["gap_reason"] == "searched_not_found"
    assert datum["note"]


def test_the_conversion_is_idempotent():
    org = {
        "data_gaps": ["nepal_presence.mode"],
        "nepal_presence": {
            "mode": {"value": "unknown", "source_url": None, "retrieved_at": "2026-08-28", "verification": "unverified"}
        },
    }
    convert(org)
    assert convert(org) == 0


def test_is_unsourced_unknown_only_matches_the_unsourced_case():
    assert is_unsourced_unknown({"value": "unknown", "source_url": None}) is True
    assert is_unsourced_unknown({"value": "unknown", "source_url": "https://e/x"}) is False
    assert is_unsourced_unknown({"value": "own_staff", "source_url": None}) is False
    assert is_unsourced_unknown({"value": None, "source_url": None}) is False


# --- the migrated dataset ----------------------------------------------------------------------


def test_no_value_carrying_datum_lacks_a_source_url():
    """The invariant the database enforces, checked against the file the database is loaded from.
    This is the assertion that was failing before the migration."""
    offenders = [
        (org["org_id"], path)
        for org in load_orgs()
        for path, datum in walk_datums(org)
        if datum.get("value") is not None and not datum.get("source_url")
    ]
    assert offenders == [], f"values with no source: {offenders}"


def test_the_seven_records_are_now_gaps_with_a_reason():
    orgs = {org["org_id"]: org for org in load_orgs()}
    expected = [
        "globalgiving",
        "care-nepal",
        "lutheran-world-federation-nepal",
        "wateraid-nepal",
        "vishwa-hindu-parishad-nepal",
        "kiwanis-club-rupandehi-lumbini",
        "the-rising-youth-club",
    ]
    for org_id in expected:
        datum = orgs[org_id]["nepal_presence"]["mode"]
        assert datum["value"] is None, org_id
        assert datum["gap_reason"] in GAP_REASON, org_id
        assert (datum.get("note") or "").strip(), org_id


def test_the_counts_after_the_migration():
    """Seven datums moved from the value side to the gap side: 157/263 became 150/270.

    430/154/276 since schema v0.5 added the Prime Minister Disaster Relief Fund - four sourced
    values (legal name, local script, presence mode, donation channel) and six gaps.
    """
    orgs = load_orgs()
    datums = [d for o in orgs for _, d in walk_datums(o)]
    assert len(datums) == 430
    assert sum(1 for d in datums if d.get("value") is not None) == 154
    assert sum(1 for d in datums if d.get("value") is None) == 276
