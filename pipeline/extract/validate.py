"""The verbatim gate.

An LLM will happily produce a fluent sentence that nobody wrote. Every claim it returns must be
provable against the report's own text, or it does not become a published statement - dropped
rather than softened. This module is that proof, and it is the reason this product can be trusted:
build and test it before the client, before the prompt, before anything that talks to a model.

Hot path: gate() runs once per extracted claim - a few dozen per report, at most 25 reports per
run - over strings bounded at a 40-word quote and a body of a few thousand characters. Nothing
here scales with the size of the dataset; the actual expensive operation in this package is the
LLM call in extract.client.extract(), which happens once per report, never once per claim.
"""

from __future__ import annotations

import html
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

MAX_QUOTE_WORDS = 40

# NFKC folds compatibility forms but explicitly does NOT fold curly quotes or dashes to their
# ASCII equivalents (core/normalise.py in this repo hit exactly this while writing alias_norm).
# U+02BC (modifier letter apostrophe) is included for the same reason that file lists it.
# Same convention as core/normalise.py's _INTRA_WORD: the ambiguous characters here are the ones
# deliberately being normalised, so each gets its own noqa rather than suppressing the file.
_CURLY_TO_ASCII = {
    "‘": "'",  # noqa: RUF001 - left single quotation mark
    "’": "'",  # noqa: RUF001 - right single quotation mark
    "‚": "'",  # noqa: RUF001 - single low-9 quotation mark
    "‛": "'",  # noqa: RUF001 - single high-reversed-9 quotation mark
    "ʼ": "'",  # noqa: RUF001 - modifier letter apostrophe
    "′": "'",  # noqa: RUF001 - prime
    "“": '"',
    "”": '"',
    "„": '"',
    "‟": '"',
    "″": '"',
    "‐": "-",  # noqa: RUF001 - hyphen
    "‑": "-",  # noqa: RUF001 - non-breaking hyphen
    "‒": "-",  # noqa: RUF001 - figure dash
    "–": "-",  # noqa: RUF001 - en dash
    "—": "-",
    "―": "-",
}

_WHITESPACE = re.compile(r"\s+")
_NBSP = " "  # noqa: RUF001 - the non-breaking space this constant folds away

# A number "as the source wrote it": digits with commas/periods used as separators, e.g. "25,000".
_DIGIT_TOKEN = re.compile(r"\d[\d,.]*")
_SCALE_WORD = re.compile(r"^[a-z]+")
_SCALE_WORDS: dict[str, Decimal] = {
    "thousand": Decimal(1_000),
    "million": Decimal(1_000_000),
    "billion": Decimal(1_000_000_000),
}


def normalise(text: str) -> str:
    """Canonicalise text so a quote and its source can be compared by simple substring search.

    In order: unescape HTML entities, Unicode-normalise (NFKC), casefold, fold curly quotes and
    dashes to their ASCII equivalents, fold non-breaking spaces to plain spaces, collapse runs of
    whitespace to a single space, strip.

    Casefold is not cosmetic here: the golden fixture quotes a mid-sentence phrase whose first
    word is sentence-initial (capitalised) in the source but returned lowercase by the model, and
    the reverse. The gate exists to catch fabricated content, not a capitalisation difference that
    carries no information about whether the words are real.
    """
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    text = "".join(_CURLY_TO_ASCII.get(ch, ch) for ch in text)
    text = text.replace(_NBSP, " ")
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def quote_offset(quote: str, body: str) -> int | None:
    """Index of `quote` inside the normalised `body`, or None when it is not a substring."""
    index = normalise(body).find(normalise(quote))
    return index if index >= 0 else None


def is_verbatim(quote: str, body: str) -> bool:
    """True when `quote`, after normalisation, appears verbatim inside `body`."""
    return quote_offset(quote, body) is not None


def word_count(quote: str) -> int:
    """Number of whitespace-separated words in the normalised quote. Empty quote counts as 0."""
    normalised = normalise(quote)
    return len(normalised.split(" ")) if normalised else 0


def _parse_digit_token(token: str) -> Decimal | None:
    cleaned = token.strip(".,").replace(",", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def amount_is_supported(amount: Decimal | None, quote: str) -> bool:
    """True when a digit token in the quote, read as the source wrote it, produces `amount`.

    Two forms are recognised: a bare number ("500 tarpaulins" supports 500) and a number
    immediately followed by a scale word ("nearly CHF 1 million" supports 1_000_000). Nothing
    else is inferred - no unit conversion, no adding up multiple numbers, no reading the number
    out of prose that does not contain it. An amount the quote does not contain, as written, is a
    number nobody sourced. Dropping it is cheap; publishing an invented one is not.
    """
    if amount is None:
        return False
    normalised = normalise(quote)
    for match in _DIGIT_TOKEN.finditer(normalised):
        value = _parse_digit_token(match.group())
        if value is None:
            continue
        if value == amount:
            return True
        rest = normalised[match.end() :].lstrip()
        scale_match = _SCALE_WORD.match(rest)
        if scale_match:
            scale = _SCALE_WORDS.get(scale_match.group())
            if scale is not None and value * scale == amount:
                return True
    return False


def gate(claim: dict[str, Any], body: str) -> tuple[Literal["auto", "rejected_unverbatim"], dict[str, Any]]:
    """The verbatim gate. Every extracted claim passes through this before it may become a row.

    Rejects a claim whose quote is not a real, at-most-40-word substring of the report body. An
    accepted claim gets its quote_offset filled in; if its amount is not supported by a digit
    token inside the quote, the amount and currency are dropped to None and the reason is recorded
    in the note - an invented number is worse than a missing one. amount_basis is never touched
    here: it was set once, by the model reading the activity sentence, and nothing in this function
    reads a note to decide it.
    """
    result = dict(claim)
    quote = result.get("quote") or ""

    if word_count(quote) > MAX_QUOTE_WORDS:
        return "rejected_unverbatim", result

    offset = quote_offset(quote, body)
    if offset is None:
        return "rejected_unverbatim", result
    result["quote_offset"] = offset

    amount = result.get("amount")
    if amount is not None and not amount_is_supported(amount, quote):
        result["amount"] = None
        result["currency"] = None
        reason = "amount dropped: not supported by the quote as written"
        existing_note = result.get("note")
        result["note"] = f"{existing_note}; {reason}" if existing_note else reason

    return "auto", result
