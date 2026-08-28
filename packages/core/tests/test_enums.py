"""Enum values are the single source for every Postgres CHECK constraint and for /v1/meta/enums.

If these tests and schema/org.schema.json ever disagree, the API and the data contract disagree.
"""

import json
from pathlib import Path

from core import enums

REPO = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((REPO / "schema" / "org.schema.json").read_text(encoding="utf-8"))


def test_check_in_builds_a_quoted_sql_in_expression():
    assert enums.check_in("org_type", ("a", "b")) == "org_type IN ('a', 'b')"


def test_gap_reason_has_exactly_the_four_spec_values_in_order():
    assert enums.GAP_REASON == ("not_searched", "searched_not_found", "source_unreachable", "not_public")


def test_verification_matches_the_json_schema_enum():
    assert list(enums.VERIFICATION) == SCHEMA["$defs"]["verification"]["enum"]


def test_org_type_matches_the_json_schema_enum():
    assert list(enums.ORG_TYPE) == SCHEMA["properties"]["org_type"]["enum"]


def test_registry_matches_the_json_schema_enum():
    schema_registry = SCHEMA["properties"]["registrations"]["items"]["properties"]["registry"]["enum"]
    assert list(enums.REGISTRY) == schema_registry


def test_warning_type_matches_the_json_schema_enum():
    schema_warning = SCHEMA["properties"]["warnings"]["items"]["properties"]["type"]["enum"]
    assert list(enums.WARNING_TYPE) == schema_warning


def test_presence_mode_matches_the_json_schema_enum():
    """The schema enum also carries null since v0.3, because a presence mode can be a gap. The
    Python tuple lists only the real values - a gap is expressed by value IS NULL, not by a
    member called "null"."""
    schema_mode = SCHEMA["$defs"]["datum_presence_mode"]["allOf"][1]["properties"]["value"]["enum"]
    assert list(enums.PRESENCE_MODE) == [value for value in schema_mode if value is not None]
    assert None in schema_mode


def test_activity_type_contains_the_three_classes_the_spec_added():
    for value in ("presence_declared", "staff_deployed", "needs_statement"):
        assert value in enums.ACTIVITY_TYPE


def test_no_enum_value_implies_a_ranking():
    forbidden = {"score", "grade", "rank", "rating", "tier", "best", "worst", "good", "bad"}
    for name in dir(enums):
        if name.startswith("_"):
            continue
        values = getattr(enums, name)
        if isinstance(values, tuple):
            for value in values:
                assert not (forbidden & set(value.lower().split("_"))), f"{name} contains a ranking word: {value}"


def test_every_enum_is_a_tuple_of_unique_strings():
    assert enums.ALL_ENUMS, "no enums registered"
    for name, values in enums.ALL_ENUMS.items():
        assert isinstance(values, tuple), name
        assert all(isinstance(v, str) for v in values), name
        assert len(set(values)) == len(values), f"{name} has duplicates"


def test_all_enums_registry_covers_every_exported_tuple():
    """/v1/meta/enums serves ALL_ENUMS. An enum missing from it is invisible to the frontend."""
    exported = {n for n in dir(enums) if n.isupper() and isinstance(getattr(enums, n), tuple)}
    registered = {n.upper() for n in enums.ALL_ENUMS}
    assert exported == registered, f"not in ALL_ENUMS: {sorted(exported - registered)}"
