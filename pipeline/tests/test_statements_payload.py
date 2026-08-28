"""Whatever shape the model puts `statements` in, the client turns it into claim dicts or nothing.

The schema asks for an array of objects. On the first live run the model returned it as a
JSON *string* containing that array, so `list.extend` iterated the string's characters and the job
died on `dict("[")` with "dictionary update sequence element #0 has length 1; 2 is required".

The golden fixture had a real list, because it was assembled by hand from a recorded run. That is
the gap this file closes: a fixture proves the happy path, and the happy path is not what a live
model necessarily sends.
"""

from __future__ import annotations

import json

import pytest

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


# --- the response schema itself ---------------------------------------------------------------


def test_the_response_schema_is_strict():
    """Two live runs returned claims missing a required field - 18 of 41, then 13 of 57. Both times
    the schema already listed `required` and the request already said strict; both times it was
    advertised through a tool call, which this route does not enforce. Sent as a structured output
    it is enforced, so a claim with no quote - a claim with no evidence - cannot come back."""
    from pipeline.extract.prompt import RESPONSE_FORMAT

    assert RESPONSE_FORMAT["json_schema"]["strict"] is True
    assert RESPONSE_FORMAT["json_schema"]["schema"]["additionalProperties"] is False


def test_every_statement_field_is_required_and_optionality_is_a_nullable_type():
    """Strict mode requires every property in `required`. Fields that are logically optional say
    so with a nullable type, which is also the honest encoding: "the text states no date" is a
    fact about the report, not a missing key."""
    from pipeline.extract.prompt import STATEMENT_SCHEMA

    assert set(STATEMENT_SCHEMA["required"]) == set(STATEMENT_SCHEMA["properties"])
    assert STATEMENT_SCHEMA["additionalProperties"] is False
    for optional in ("happened_on", "amount", "currency"):
        assert "null" in STATEMENT_SCHEMA["properties"][optional]["type"], optional


# --- the response body ------------------------------------------------------------------------


def test_a_well_formed_response_body_is_returned_as_a_dict():
    from pipeline.extract.client import _payload

    assert _payload('{"statements": []}') == {"statements": []}


@pytest.mark.parametrize(
    ("content", "expected_event"),
    [
        (None, "extract_response_empty"),
        ("", "extract_response_empty"),
        ("I could not find any statements.", "extract_response_not_json"),
        ("[1, 2, 3]", "extract_response_not_an_object"),
    ],
)
def test_a_response_the_schema_should_have_prevented_is_logged_not_swallowed(content, expected_event, monkeypatch):
    """An enforced schema should make every one of these unreachable, so reaching one is not a
    claim being rejected - it is the enforcement not holding, and it has to be visible at error
    level. Returning an empty payload rather than raising keeps one bad response from ending a run
    that has already paid for every call before it.

    Stubbed at the module's `log` attribute for the reason written out in test_match.py: the
    `spenden` logger tree sets propagate=False, so caplog's root handler never sees these records.
    """
    from pipeline.extract import client as client_module

    events: list[str] = []

    class _StubLog:
        def error(self, message: str, extra: dict | None = None) -> None:
            events.append(message)

    monkeypatch.setattr(client_module, "log", _StubLog())

    assert client_module._payload(content) == {}
    assert events == [expected_event]
