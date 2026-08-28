"""Deriving gap_reason from what the researchers actually wrote.

The rules are matched against the real note strings in the pilot dataset, not against invented
ones. Nothing here invents a claim: the generated note states only what the record already implies
through data_gaps.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.migrations.add_gap_reason import (
    GENERATED_NOTE,
    derive_gap_reason,
    derive_registration_gap_reason,
    load_orgs,
    migrate_org,
    normalise_path,
    walk_datums,
)

REPO = Path(__file__).resolve().parents[2]
GAP_REASON = ("not_searched", "searched_not_found", "source_unreachable", "not_public")

# Every case below is a note string that exists in data/orgs/batch-*.json, or a direct negation.
CASES = [
    (
        {"value": None, "note": "swc.org.np was unreachable during this research session."},
        "x",
        set(),
        "source_unreachable",
    ),
    (
        {"value": None, "note": "Charity Commission accounts page returned 403 to WebFetch"},
        "x",
        set(),
        "source_unreachable",
    ),
    (
        {"value": None, "note": "IFRC 2024 Annual Report PDF located but its content could not be read this session"},
        "x",
        set(),
        "source_unreachable",
    ),
    (
        {"value": None, "note": "ifrc.org returned HTTP 403 on direct WebFetch of the annual report"},
        "x",
        set(),
        "source_unreachable",
    ),
    ({"value": None, "note": "The register does not publish this figure"}, "x", set(), "not_public"),
    ({"value": None, "note": "wird nicht veroeffentlicht"}, "x", set(), "not_public"),
    (
        {"value": None, "note": "No published expenditure split found within research budget."},
        "p",
        set(),
        "searched_not_found",
    ),
    ({"value": None, "note": "Not found within research budget."}, "p", set(), "searched_not_found"),
    (
        {"value": None, "note": None},
        "financial_transparency.income",
        {"financial_transparency.income"},
        "searched_not_found",
    ),
    ({"value": None, "note": ""}, "names.local_script", set(), "not_searched"),
    ({"value": None, "note": None}, "names.local_script", set(), "not_searched"),
]


@pytest.mark.parametrize(("datum", "path", "gaps", "expected"), CASES)
def test_derive_gap_reason(datum, path, gaps, expected):
    assert derive_gap_reason(datum, path, gaps) == expected


def test_an_unreachable_source_beats_a_not_public_claim():
    """An unreachable source cannot tell us what it publishes, so it must not be recorded as if
    it had. Order of the rules is the assertion here."""
    datum = {"value": None, "note": "The register was unreachable, so we cannot say what it publishes"}
    assert derive_gap_reason(datum, "x", set()) == "source_unreachable"


def test_a_datum_with_a_value_never_gets_a_gap_reason():
    assert derive_gap_reason({"value": 5, "note": "unreachable"}, "x", set()) is None
    assert derive_gap_reason({"value": False, "note": None}, "x", set()) is None
    assert derive_gap_reason({"value": 0, "note": None}, "x", set()) is None


def test_a_generated_note_is_not_read_back_as_evidence_of_a_search():
    """Regression. The generated note for not_searched said "Not searched in this research pass.",
    and the next run saw a non-empty note, concluded a researcher had looked, and reclassified the
    gap as searched_not_found. Twenty gaps flipped on the second run of the real migration."""
    datum = {"value": None, "note": GENERATED_NOTE["not_searched"]}
    assert derive_gap_reason(datum, "names.local_script", set()) == "not_searched"


def test_every_generated_note_survives_a_second_classification():
    """Each generated note must classify back to the reason that produced it, under the conditions
    that produced it, or the migration walks the dataset in circles.

    searched_not_found is only ever generated for a path that is listed in data_gaps, so that is
    the state it has to stay stable in.
    """
    states = {
        "searched_not_found": ("financial_transparency.income", {"financial_transparency.income"}),
        "not_searched": ("names.local_script", set()),
        "source_unreachable": ("registrations[0].identifier", set()),
        "not_public": ("financial_transparency.program_ratio", set()),
    }
    for reason, note in GENERATED_NOTE.items():
        path, gaps = states[reason]
        assert derive_gap_reason({"value": None, "note": note}, path, gaps) == reason, note


def test_migrating_an_already_migrated_record_changes_nothing():
    org = {
        "org_id": "x",
        "data_gaps": ["financial_transparency.income"],
        "registrations": [{"registry": "NP_SWC", "identifier": None, "note": None}],
        "financial_transparency": {
            "income": {"value": None, "source_url": None, "retrieved_at": "2026-08-28", "verification": "unverified"}
        },
        "names": {
            "local_script": {
                "value": None,
                "source_url": None,
                "retrieved_at": "2026-08-28",
                "verification": "unverified",
            }
        },
    }
    first = migrate_org(org)
    assert first > 0
    assert migrate_org(org) == 0, "second pass must be a no-op"


def test_normalise_path_collapses_array_indices():
    assert normalise_path("registrations[2].identifier") == "registrations[].identifier"
    assert normalise_path("financial_transparency.income") == "financial_transparency.income"


def test_a_registration_with_an_identifier_gets_no_reason():
    assert derive_registration_gap_reason({"identifier": "1234567", "note": None}) is None


def test_a_registration_without_an_identifier_and_an_unreachable_note():
    reg = {"identifier": None, "note": "swc.org.np was unreachable during this research session."}
    assert derive_registration_gap_reason(reg) == "source_unreachable"


# --- the migrated dataset ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def orgs() -> list[dict]:
    return load_orgs()


def test_every_gap_in_every_batch_has_a_reason_and_a_note(orgs):
    offenders = [
        (org["org_id"], path)
        for org in orgs
        for path, datum in walk_datums(org)
        if datum.get("value") is None
        and not (datum.get("gap_reason") in GAP_REASON and (datum.get("note") or "").strip())
    ]
    assert offenders == [], f"gaps without a reason or a note: {offenders[:10]}"


def test_no_value_carrying_datum_gained_a_gap_reason(orgs):
    offenders = [
        (org["org_id"], path)
        for org in orgs
        for path, datum in walk_datums(org)
        if datum.get("value") is not None and datum.get("gap_reason") is not None
    ]
    assert offenders == []


def test_every_registration_without_an_identifier_says_why(orgs):
    offenders = [
        (org["org_id"], reg.get("registry"))
        for org in orgs
        for reg in org["registrations"]
        if reg.get("identifier") is None and reg.get("gap_reason") not in GAP_REASON
    ]
    assert offenders == []


def test_the_generated_notes_are_exactly_the_reviewed_wording():
    """These four strings are published to readers. They are pinned here so a later edit has to be
    a deliberate, reviewed change of what the site tells people. Each is a statement about our
    research or about the source; none asserts anything about the organisation."""
    assert GENERATED_NOTE == {
        "searched_not_found": "Searched in the 2026-08-28 research pass; not found.",
        "not_searched": "Not searched in this research pass.",
        "source_unreachable": "Source did not answer during the 2026-08-28 research pass.",
        "not_public": "Source states this is not published.",
    }


def test_generated_notes_are_actually_used_in_the_dataset(orgs):
    generated = set(GENERATED_NOTE.values())
    used = [datum for org in orgs for _, datum in walk_datums(org) if datum.get("note") in generated]
    assert used, "no generated notes present - did the migration run?"


def test_the_dataset_still_validates_and_still_has_45_orgs():
    report = json.loads((REPO / "data" / "raw" / "orgs" / "_validation.json").read_text(encoding="utf-8"))["data"]
    assert report["schema_errors"] == 0
    assert report["orgs"] == 45  # v0.5 added the Prime Minister Disaster Relief Fund


def test_the_gap_reason_distribution_is_recorded(orgs):
    """Pins the shape of the result so an accidental re-run that reclassifies everything as
    not_searched cannot pass silently."""
    counts: dict[str, int] = {}
    for org in orgs:
        for _, datum in walk_datums(org):
            reason = datum.get("gap_reason")
            if reason:
                counts[reason] = counts.get(reason, 0) + 1
    # 270 since schema v0.3, when seven unsourced nepal_presence.mode values became real gaps;
    # 276 since v0.5 added the government fund record and its six unpublished figures.
    assert sum(counts.values()) == 276, counts
    assert counts["searched_not_found"] > counts.get("not_searched", 0)
    assert counts.get("source_unreachable", 0) >= 5
