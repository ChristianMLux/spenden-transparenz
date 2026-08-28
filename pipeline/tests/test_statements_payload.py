"""Whatever shape the model puts `statements` in, the client turns it into claim dicts or nothing.

The tool schema asks for an array of objects. On the first live run the model returned it as a
JSON *string* containing that array, so `list.extend` iterated the string's characters and the job
died on `dict("[")` with "dictionary update sequence element #0 has length 1; 2 is required".

The golden fixture had a real list, because it was assembled by hand from a recorded run. That is
the gap this file closes: a fixture proves the happy path, and the happy path is not what a live
model necessarily sends.
"""

from __future__ import annotations

import json

from pipeline.extract.client import _statements


def test_a_real_list_passes_through():
    assert _statements([{"quote": "a"}, {"quote": "b"}]) == [{"quote": "a"}, {"quote": "b"}]


def test_a_json_string_is_parsed():
    """The live failure. Some models and gateways serialise nested structures inside tool
    arguments rather than nesting them."""
    assert _statements(json.dumps([{"quote": "a"}, {"quote": "b"}])) == [{"quote": "a"}, {"quote": "b"}]


def test_a_single_object_is_wrapped():
    assert _statements({"quote": "a"}) == [{"quote": "a"}]


def test_a_json_string_holding_one_object_is_wrapped():
    assert _statements(json.dumps({"quote": "a"})) == [{"quote": "a"}]


def test_missing_statements_is_empty():
    assert _statements(None) == []


def test_unparseable_text_is_dropped_rather_than_guessed():
    """A claim we cannot parse has no quote we can verify. Inventing structure for it would put an
    unverifiable statement in front of a reader."""
    assert _statements("not json at all") == []


def test_non_object_entries_are_dropped_and_the_rest_survive():
    assert _statements([{"quote": "a"}, "junk", 7, None]) == [{"quote": "a"}]


def test_an_unexpected_type_is_dropped():
    assert _statements(42) == []
    assert _statements(True) == []


def test_an_empty_list_stays_empty():
    """A report with no organisational response is a normal, correct outcome."""
    assert _statements([]) == []
    assert _statements("[]") == []


# --- the tool schema itself -------------------------------------------------------------------


def test_the_tool_schema_is_strict():
    """A live run returned 18 of 41 claims missing a required field. The schema already listed
    `required`; nothing enforced it. strict makes the provider enforce it instead of advertising
    it, so a claim with no quote - a claim with no evidence - cannot come back at all."""
    from pipeline.extract.prompt import STATEMENT_TOOL

    assert STATEMENT_TOOL["function"]["strict"] is True
    assert STATEMENT_TOOL["function"]["parameters"]["additionalProperties"] is False


def test_every_statement_field_is_required_and_optionality_is_a_nullable_type():
    """Strict mode requires every property in `required`. Fields that are logically optional say
    so with a nullable type, which is also the honest encoding: "the text states no date" is a
    fact about the report, not a missing key."""
    from pipeline.extract.prompt import _STATEMENT_SCHEMA

    assert set(_STATEMENT_SCHEMA["required"]) == set(_STATEMENT_SCHEMA["properties"])
    assert _STATEMENT_SCHEMA["additionalProperties"] is False
    for optional in ("happened_on", "amount", "currency"):
        assert "null" in _STATEMENT_SCHEMA["properties"][optional]["type"], optional
