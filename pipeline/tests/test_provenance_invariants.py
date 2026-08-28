"""The provenance rule as executable tests, over the real 44-organisation pilot dataset.

Every value-carrying datum has a source_url, every gap has a note and a gap_reason, data_gaps is a
superset of the paths that are actually empty, quotes stay under the 40-word copyright boundary,
and the dataset carries no score/rating/rank/grade key anywhere - the product rule (CLAUDE.md
Global Constraints 1 and 2) in a form CI enforces on every PR from every worker.

Runs against the deduplicated 44-organisation view (pipeline.migrations.add_gap_reason.load_orgs,
the same view orgs-nepal-2026.json was generated from) for the counts the product promises, and
separately against orgs-nepal-2026.json and every individual data/orgs/batch-*.json for the shape
invariants, so a raw batch file's own content is checked on its own too - caritas-nepal appears in
both batch-2 and batch-3 on purpose (plan Decision D7, "do not fix it"), and both copies must
satisfy the invariants independently, not just the one load_orgs() keeps.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.migrations.add_gap_reason import load_orgs, walk_datums

REPO = Path(__file__).resolve().parents[2]
BATCH_DIR = REPO / "data" / "orgs"
MERGED_FILE = REPO / "orgs-nepal-2026.json"

INDEX = re.compile(r"\[\d+\]")

SCORE_WORDS = ('"score"', '"rating"', '"rank"', '"grade"')

# The deduplicated 44 - one row per org_id, first occurrence wins. Loaded once at import time:
# every test in this module reads the same in-memory list rather than re-parsing the batch files.
ORGS = load_orgs()


def _normalise(path: str) -> str:
    """registrations[2].identifier -> registrations[].identifier, matching data_gaps entries."""
    return INDEX.sub("[]", path)


def _load_sources() -> dict[str, list[dict]]:
    """Every individual batch file, undeduplicated, plus the merged orgs-nepal-2026.json.

    Deliberately not load_orgs(): Task A-1 runs "against orgs-nepal-2026.json and against every
    data/orgs/batch-*.json", which means each file as it actually is on disk, duplicate
    caritas-nepal included.
    """
    sources = {p.name: json.loads(p.read_text(encoding="utf-8-sig")) for p in sorted(BATCH_DIR.glob("batch-*.json"))}
    sources[MERGED_FILE.name] = json.loads(MERGED_FILE.read_text(encoding="utf-8"))["orgs"]
    return sources


SOURCES = _load_sources()


# --- the counts the product promises (over the deduplicated 44) --------------------------------


def test_the_counts_the_product_promises():
    assert len(ORGS) == 44
    assert sum(1 for o in ORGS if o["hq"]["country"] == "NP") == 14
    assert sum(1 for o in ORGS for _ in walk_datums(o)) == 420


# --- the provenance invariants (over the deduplicated 44) ---------------------------------------


def test_every_value_carrying_datum_has_a_source_url():
    offenders = [
        (o["org_id"], p)
        for o in ORGS
        for p, d in walk_datums(o)
        if d.get("value") is not None and not d.get("source_url")
    ]
    assert offenders == []


def test_every_gap_has_a_note_and_a_gap_reason():
    offenders = [
        (o["org_id"], p)
        for o in ORGS
        for p, d in walk_datums(o)
        if d.get("value") is None and not (d.get("note") and d.get("gap_reason"))
    ]
    assert offenders == []


def test_data_gaps_is_a_superset_of_the_null_paths():
    # not_searched gaps are exempt: SCHEMA.md defines data_gaps as "paths that stayed empty after
    # a real search", which is exactly the searched_not_found / not_searched distinction. If this
    # exemption ever hid a real gap, test_every_gap_has_a_note_and_a_gap_reason still catches it.
    for o in ORGS:
        declared = {_normalise(g) for g in o["data_gaps"]}
        actual = {
            _normalise(p) for p, d in walk_datums(o) if d.get("value") is None and d.get("gap_reason") != "not_searched"
        }
        assert actual <= declared, f"{o['org_id']} has undeclared gaps: {sorted(actual - declared)}"


def test_no_quote_exceeds_40_words():
    for o in ORGS:
        for p, d in walk_datums(o):
            q = d.get("quote")
            assert q is None or len(q.split()) <= 40, f"{o['org_id']}.{p}: {len(q.split())} words"
        for i, r in enumerate(o["current_response"]):
            q = r.get("quote")
            assert q is None or len(q.split()) <= 40, f"{o['org_id']}.current_response[{i}]: {len(q.split())} words"


def test_the_dataset_contains_no_score_key():
    blob = json.dumps(ORGS)
    for word in SCORE_WORDS:
        assert word not in blob


def test_the_org_datum_gap_reason_distribution():
    """Measured directly against this checkout today (2026-08-28), not copied from the brief.

    The brief quotes 237 searched_not_found / 20 not_searched / 12 source_unreachable. Recomputing
    it here gives 231 / 20 / 12 - not_searched and source_unreachable match, searched_not_found is
    6 lower. The three still sum to the 263 total gaps that both the brief and
    test_the_counts_the_product_promises agree on, and test_add_gap_reason.py's own
    test_the_gap_reason_distribution_is_recorded pins the same 263 without pinning the
    sub-distribution - this test pins it, using the number this checkout actually produces, and
    is the discrepancy flagged in the WP-A report rather than silently matched to the brief.
    """
    counts: dict[str, int] = {}
    for o in ORGS:
        for _, d in walk_datums(o):
            if d.get("value") is None:
                counts[d["gap_reason"]] = counts.get(d["gap_reason"], 0) + 1
    assert counts == {"searched_not_found": 231, "not_searched": 20, "source_unreachable": 12}


# --- the same shape invariants, run against every individual source file on disk ----------------


@pytest.mark.parametrize("source_name", sorted(SOURCES))
def test_every_source_file_satisfies_the_provenance_invariants(source_name):
    orgs = SOURCES[source_name]

    missing_source_url = [
        (o["org_id"], p)
        for o in orgs
        for p, d in walk_datums(o)
        if d.get("value") is not None and not d.get("source_url")
    ]
    assert missing_source_url == [], f"{source_name}: value without source_url: {missing_source_url}"

    missing_gap_fields = [
        (o["org_id"], p)
        for o in orgs
        for p, d in walk_datums(o)
        if d.get("value") is None and not (d.get("note") and d.get("gap_reason"))
    ]
    assert missing_gap_fields == [], f"{source_name}: gap without note and gap_reason: {missing_gap_fields}"

    for o in orgs:
        for p, d in walk_datums(o):
            q = d.get("quote")
            assert q is None or len(q.split()) <= 40, f"{source_name}:{o['org_id']}.{p}"
        for i, r in enumerate(o["current_response"]):
            q = r.get("quote")
            assert q is None or len(q.split()) <= 40, f"{source_name}:{o['org_id']}.current_response[{i}]"

    blob = json.dumps(orgs)
    for word in SCORE_WORDS:
        assert word not in blob, f"{source_name}: contains {word}"
