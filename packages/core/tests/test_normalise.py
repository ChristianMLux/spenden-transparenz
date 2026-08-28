"""Alias normalisation.

Used for both org aliases and district aliases, so extraction output can be joined to the records
without fuzzy matching. Exact normalised match only: a wrong attribution is worse than a null one.
"""

from core.normalise import alias_norm


def test_case_and_surrounding_whitespace_are_ignored():
    assert alias_norm("  Rasuwa  ") == alias_norm("rasuwa") == "rasuwa"


def test_inner_whitespace_collapses():
    assert alias_norm("Rasuwa   district") == "rasuwa district"


def test_punctuation_is_dropped():
    assert alias_norm("Chitwan district (Mugling)") == "chitwan district mugling"
    assert alias_norm("W.V. Nepal") == "wv nepal"


def test_unicode_is_normalised_but_scripts_are_kept():
    """Devanagari names stay usable as aliases; they are not transliterated away."""
    assert alias_norm("नेपाल") == "नेपाल"


def test_curly_punctuation_matches_its_ascii_form():
    assert alias_norm("People’s Aid") == alias_norm("People's Aid")  # noqa: RUF001


def test_an_empty_or_punctuation_only_string_normalises_to_empty():
    assert alias_norm("") == ""
    assert alias_norm("   ") == ""
    assert alias_norm("---") == ""


def test_normalisation_is_idempotent():
    once = alias_norm("Chitwan district (Mugling)")
    assert alias_norm(once) == once


def test_chitwan_and_chitawan_stay_different():
    """HAPI spells it Chitawan, the org records say Chitwan. Normalisation must not paper over
    that: it is a real spelling difference and needs a deliberate alias row, not a fuzzy match."""
    assert alias_norm("Chitwan") != alias_norm("Chitawan")
