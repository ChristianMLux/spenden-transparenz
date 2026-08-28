"""data_gaps must agree with the datums it summarises.

CLAUDE.md's first invariant requires data_gaps to be a superset of the null paths. Five records
contradicted it: the researcher's note said they searched and found nothing, but the path was
missing from the list.
"""

from __future__ import annotations

from pipeline.migrations.add_gap_reason import load_orgs, normalise_path, walk_datums
from pipeline.migrations.complete_data_gaps import SEARCHED, complete, missing_paths


def test_a_searched_gap_missing_from_the_list_is_added():
    org = {
        "org_id": "x",
        "data_gaps": [],
        "financial_transparency": {
            "program_ratio": {
                "value": None,
                "source_url": None,
                "retrieved_at": "2026-08-28",
                "verification": "unverified",
                "note": "No published expenditure split found within research budget.",
                "gap_reason": "searched_not_found",
            }
        },
    }
    assert complete(org) == 1
    assert "financial_transparency.program_ratio" in org["data_gaps"]


def test_a_not_searched_gap_is_left_out():
    """SCHEMA.md defines data_gaps as paths that stayed empty after a real search. Listing
    something nobody searched for would make the list claim more than the research does."""
    org = {
        "org_id": "x",
        "data_gaps": [],
        "names": {
            "local_script": {
                "value": None,
                "source_url": None,
                "retrieved_at": "2026-08-28",
                "verification": "unverified",
                "note": "Not searched in this research pass.",
                "gap_reason": "not_searched",
            }
        },
    }
    assert complete(org) == 0
    assert org["data_gaps"] == []


def test_nothing_is_ever_removed():
    """data_gaps also names paths that are not datum nodes - register identifiers, the website,
    the whole current_response array. Those declarations are the researcher's."""
    org = {
        "org_id": "x",
        "data_gaps": ["registrations[NP_SWC].identifier", "website", "current_response"],
        "names": {},
    }
    complete(org)
    assert org["data_gaps"] == ["registrations[NP_SWC].identifier", "website", "current_response"]


def test_completion_is_idempotent():
    org = {
        "org_id": "x",
        "data_gaps": [],
        "financial_transparency": {
            "income": {
                "value": None,
                "source_url": None,
                "retrieved_at": "2026-08-28",
                "verification": "unverified",
                "note": "searched, nothing published",
                "gap_reason": "searched_not_found",
            }
        },
    }
    complete(org)
    assert complete(org) == 0


# --- the migrated dataset ----------------------------------------------------------------------


def test_every_searched_gap_in_the_dataset_is_declared():
    offenders = [(org["org_id"], path) for org in load_orgs() for path in missing_paths(org)]
    assert offenders == [], f"searched gaps missing from data_gaps: {offenders}"


def test_data_gaps_is_a_superset_of_the_searched_null_paths():
    """The invariant as CLAUDE.md states it, over the real records."""
    for org in load_orgs():
        declared = {normalise_path(gap) for gap in org["data_gaps"]}
        actual = {
            normalise_path(path)
            for path, datum in walk_datums(org)
            if datum.get("value") is None and datum.get("gap_reason") in SEARCHED
        }
        assert actual <= declared, f"{org['org_id']}: {sorted(actual - declared)}"
