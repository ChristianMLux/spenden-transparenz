"""Alias normalisation, shared by org matching and district resolution.

Matching is exact-on-normalised-form, never fuzzy. A wrong organisation attributed to a relief
activity is worse than no attribution at all, and "named but not identified" is a designed,
visible state in this product rather than a failure to paper over.

So this function only removes noise that is certainly noise: case, surrounding and repeated
whitespace, punctuation, and Unicode composition differences. It does not transliterate, stem or
approximate. Chitwan and Chitawan stay different words, which is why they need a deliberate alias
row rather than a clever matcher.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")

# Punctuation that sits inside a word rather than between words. Dropping it without leaving a
# space is what makes "W.V. Nepal" and "WV Nepal" the same alias; replacing it with a space would
# produce "w v nepal" and they would never match.
# The curly forms are deliberate and load-bearing: NFKC does not fold U+2019 or U+02BC to the
# ASCII apostrophe, so listing them here is what makes "People's Aid" match the curly spelling.
_INTRA_WORD = ".'’ʼ"  # noqa: RUF001 - the ambiguous characters are the ones being normalised


def _keep(char: str) -> bool:
    """Letters, digits, combining marks and whitespace survive; punctuation and symbols do not.

    The combining-mark case is load-bearing: Devanagari vowel signs are category Mn, and Python's
    \\w does not match them. A \\w-based filter turns नेपाल into नपल, which silently mangles every
    Devanagari organisation name the product displays.
    """
    if char.isspace():
        return True
    return unicodedata.category(char)[0] in {"L", "N", "M"}


def alias_norm(value: str) -> str:
    """Normalise a name for exact alias matching. Idempotent."""
    # NFKC folds compatibility forms and curly punctuation towards their canonical shape while
    # leaving Devanagari and other scripts intact.
    text = unicodedata.normalize("NFKC", value).casefold()
    text = "".join("" if char in _INTRA_WORD else char if _keep(char) else " " for char in text)
    return _WHITESPACE.sub(" ", text).strip()
