"""The verbatim gate: normalisation, is_verbatim, quote_offset, word_count, amount_is_supported,
and gate() itself.

This is the single most important file in WP-B. An LLM will happily produce a fluent sentence that
nobody wrote; every claim it returns must be provable against the source text, or it is discarded
rather than softened. These tests exist to make that provable, not merely asserted.

The non-breaking space fixture is written as a \\xa0 escape (plain ASCII in the source, so nothing
for a diff to silently corrupt); the curly apostrophe and em dash are single named constants below,
each carrying its own ruff RUF001 exemption, so the character these tests exist to check for is
declared exactly once.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.extract.validate import (
    amount_is_supported,
    gate,
    is_verbatim,
    normalise,
    quote_offset,
    word_count,
)

CURLY_APOSTROPHE = "’"  # noqa: RUF001 - the character normalise() is being tested against
EM_DASH = "—"
NBSP = "\xa0"

# --- normalise -----------------------------------------------------------------------------


def test_normalise_unescapes_html_entities():
    assert normalise("caf&eacute; kitchens") == "café kitchens"


def test_normalise_folds_curly_quotes_and_dashes_to_ascii():
    assert normalise(f"It{CURLY_APOSTROPHE}s an emergency{EM_DASH}now") == "it's an emergency-now"


def test_normalise_folds_non_breaking_spaces_and_collapses_whitespace():
    assert normalise(f"distributed{NBSP}500" + " " * 3 + "tarpaulins") == "distributed 500 tarpaulins"


def test_normalise_strips_leading_and_trailing_whitespace():
    assert normalise("  hello world  ") == "hello world"


def test_normalise_is_idempotent():
    once = normalise(f"It{CURLY_APOSTROPHE}s" + " " * 3 + "messy text.")
    assert normalise(once) == once


# --- is_verbatim -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("quote", "body", "expected"),
    [
        ("distributed 500 tarpaulins", "It distributed 500 tarpaulins in Rasuwa.", True),
        ("distributed" + "  500" + "   tarpaulins", "It distributed 500 tarpaulins.", True),  # whitespace
        (f"we{CURLY_APOSTROPHE}ve deployed teams", "We've deployed teams.", True),  # curly apostrophe
        ("caf&eacute; kitchens", "Cafe kitchens were opened.", False),  # entity but different word
        ("deployed 12 medical teams", "Deployed 12 medical teams", True),
        ("provided emergency shelter", "The agency provided food and water.", False),  # not in the body
    ],
)
def test_is_verbatim(quote, body, expected):
    assert is_verbatim(quote, body) is expected


# --- quote_offset / word_count -----------------------------------------------------------------


def test_quote_offset_returns_the_index_in_the_normalised_body():
    body = "It distributed 500 tarpaulins in Rasuwa."
    assert quote_offset("500 tarpaulins", body) == normalise(body).find("500 tarpaulins")


def test_quote_offset_is_none_when_the_quote_is_not_in_the_body():
    assert quote_offset("we rescued 4000 people", "No such sentence here.") is None


def test_word_count_counts_normalised_words():
    assert word_count("distributed" + "  500" + "   tarpaulins") == 3


def test_word_count_of_empty_quote_is_zero():
    assert word_count("") == 0


# --- amount_is_supported ------------------------------------------------------------------------


def test_amount_is_supported_by_a_bare_digit_token():
    assert amount_is_supported(Decimal("500"), "distributed 500 tarpaulins") is True


def test_amount_is_supported_by_a_number_with_a_scale_word():
    assert amount_is_supported(Decimal("1000000"), "released nearly CHF 1 million in funding") is True
    assert amount_is_supported(Decimal("25000000"), "an Emergency Appeal for CHF 25 million") is True


def test_amount_is_not_supported_when_the_quote_has_no_digits():
    assert amount_is_supported(Decimal("1000000"), "released emergency funding") is False


def test_amount_is_not_supported_when_no_digit_token_produces_it():
    # the quote contains a number, but not the number in question
    assert amount_is_supported(Decimal("1000000"), "distributed 500 tarpaulins") is False


def test_amount_is_supported_returns_false_for_none():
    assert amount_is_supported(None, "distributed 500 tarpaulins") is False


# --- gate ----------------------------------------------------------------------------------------


def test_gate_rejects_a_hallucinated_quote():
    status, _claim = gate({"quote": "we rescued 4000 people", "amount": None}, "No such sentence here.")
    assert status == "rejected_unverbatim"


def test_gate_rejects_an_empty_quote():
    """str.find("") is 0 for any body, so an empty quote would otherwise read as verbatim at
    offset 0 - a claim with no evidence at all passing as the most-verified kind of claim there is.
    This is precisely the case the gate exists to catch: not a fabricated quote, but no quote."""
    status, _claim = gate({"quote": ""}, "Any body text here.")
    assert status == "rejected_unverbatim"


def test_gate_rejects_a_none_quote():
    status, _claim = gate({"quote": None}, "Any body text here.")
    assert status == "rejected_unverbatim"


def test_gate_rejects_a_whitespace_only_quote():
    status, _claim = gate({"quote": "   "}, "Any body text here.")
    assert status == "rejected_unverbatim"


def test_gate_rejects_a_claim_with_no_quote_key_at_all():
    status, _claim = gate({}, "Any body text here.")
    assert status == "rejected_unverbatim"


def test_gate_drops_an_amount_the_quote_does_not_contain():
    status, claim = gate(
        {"quote": "released emergency funding", "amount": Decimal("1000000"), "currency": "CHF"},
        "IFRC released emergency funding for the response.",
    )
    assert status == "auto"
    assert claim["amount"] is None and claim["currency"] is None
    assert "not supported by the quote" in claim["note"]


def test_gate_keeps_an_amount_the_quote_does_contain():
    status, claim = gate(
        {"quote": "nearly CHF 1 million", "amount": Decimal("1000000"), "currency": "CHF"},
        "It released nearly CHF 1 million.",
    )
    assert status == "auto" and claim["amount"] == Decimal("1000000")


def test_quote_longer_than_40_words_is_rejected():
    long_quote = " ".join(["word"] * 41)
    status, _ = gate({"quote": long_quote}, long_quote)
    assert status == "rejected_unverbatim"


def test_gate_sets_quote_offset_on_an_accepted_claim():
    body = "It distributed 500 tarpaulins in Rasuwa."
    status, claim = gate({"quote": "500 tarpaulins"}, body)
    assert status == "auto"
    assert claim["quote_offset"] == normalise(body).find("500 tarpaulins")


def test_gate_preserves_the_rest_of_the_claim_dict():
    _status, claim = gate(
        {"quote": "500 tarpaulins", "org_name_raw": "Nepal Red Cross", "activity_type": "relief_distribution"},
        "It distributed 500 tarpaulins in Rasuwa.",
    )
    assert claim["org_name_raw"] == "Nepal Red Cross"
    assert claim["activity_type"] == "relief_distribution"


def test_gate_never_derives_amount_basis_from_a_note_mentioning_disbursed():
    """Notes elsewhere in this dataset routinely read "not confirmed disbursed" on pledges and
    appeals. gate() must never let a note override amount_basis: that field is set once, by the
    model reading the activity sentence, and gate() only ever touches amount/currency/quote_offset.
    A note-matching implementation would turn every appeal into a disbursement - the exact
    inversion of what actually happened.
    """
    claim = {
        "quote": "has launched an Emergency Appeal for CHF 25 million",
        "amount": Decimal("25000000"),
        "currency": "CHF",
        "amount_basis": "appeal",
        "note": "not confirmed disbursed",
    }
    body = "IFRC has launched an Emergency Appeal for CHF 25 million to support the response."
    status, result = gate(claim, body)
    assert status == "auto"
    assert result["amount_basis"] == "appeal"
    assert result["amount"] == Decimal("25000000")
