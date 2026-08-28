"""The published data contract must carry gap_reason.

Without it, "we did not look", "we looked and found nothing", "the register did not answer" and
"the register does not publish this" all render as the same empty cell. Three different honesty
claims collapsing into one is the failure this whole product exists to avoid.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "schema" / "org.schema.json").read_text(encoding="utf-8"))
SCHEMA_MD = (REPO / "SCHEMA.md").read_text(encoding="utf-8")

EXPECTED = ["not_searched", "searched_not_found", "source_unreachable", "not_public", None]


def test_gap_reason_is_defined_once_with_the_four_values_and_null():
    field = SCHEMA["$defs"]["gap_reason"]
    assert field["enum"] == EXPECTED
    assert field["type"] == ["string", "null"]


def test_datum_base_references_that_one_definition():
    assert SCHEMA["$defs"]["datum_base"]["properties"]["gap_reason"]["$ref"] == "#/$defs/gap_reason"


def test_gap_reason_is_not_required():
    """A value-carrying datum has no reason to state one, and making it required would invalidate
    every record that already exists."""
    assert "gap_reason" not in SCHEMA["$defs"]["datum_base"].get("required", [])


def test_registration_items_may_also_carry_gap_reason():
    """A register row with identifier null is the most honest line on an organisation page. It
    needs to say why the identifier is missing just as much as a datum does."""
    props = SCHEMA["properties"]["registrations"]["items"]["properties"]
    assert props["gap_reason"]["$ref"] == "#/$defs/gap_reason"


def test_the_schema_announces_version_0_2():
    assert "v0.2" in SCHEMA["title"]


def test_schema_md_documents_gap_reason():
    assert "gap_reason" in SCHEMA_MD
    for value in ("not_searched", "searched_not_found", "source_unreachable", "not_public"):
        assert value in SCHEMA_MD, f"SCHEMA.md does not explain {value}"
