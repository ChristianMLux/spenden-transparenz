"""Prompt v2 and the tool schema for extraction.

The model reads one report's body text and returns zero or more statements: an organisation did
something, somewhere, on some date, for some amount. The tool schema mirrors response_statement so
a claim never needs reshaping before it reaches gate() and the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core import enums

PROMPT_VERSION = "v2"

STATEMENT_TOOL_NAME = "record_response_statements"

SYSTEM_PROMPT = """You extract organisational disaster-response statements from a single ReliefWeb \
report for a donor-transparency product. You are not writing a summary; you are recording claims \
that must be checked against the source text word for word, so precision matters more than \
completeness.

Rules, all mandatory:

1. Quote verbatim. Every statement's "quote" field must be copied character-for-character from \
the report text below - the exact words, in the exact order, at most 40 words. Never paraphrase, \
never summarise, never combine two sentences into one quote. If you cannot find a short exact \
quote that supports a claim, do not report the claim.
2. If an organisation is named in the report but no activity is described for it, record it once \
with activity_type "presence_declared" rather than inventing an activity.
3. Never infer a district, region or place the text does not name. "where_raw" holds only the \
place names the text itself uses, exactly as written (e.g. "Rasuwa", "Timure"). If the statement \
names no place, leave "where_raw" empty - do not guess from context or from the known districts \
below.
4. The known districts for this report are given below as CONTEXT ONLY. They tell you what this \
disaster is about; they are not evidence for any individual statement and must never be copied \
into a statement's where_raw unless the sentence you are quoting names that place itself.
5. "amount_basis" describes what kind of figure the amount is, and it must be derived only from \
what the activity sentence itself says the organisation did with the money - never from any note, \
label, or outside context you might otherwise have. "appeal" for a funding target or ask, \
"pledged" for money promised but not yet moved, "raised" for money collected from donors, \
"released" for money an organisation has freed up or allocated internally, "disbursed" only when \
the sentence itself says the money reached recipients, "reported" when the sentence does not say \
which of these it is. Do not default to "disbursed" just because a number is mentioned.
6. If the report describes no organisational response to the disaster at all, return an empty \
list of statements. An empty list is a correct answer, not a failure.

Known districts for this report (context only, not evidence): {known_districts}"""

USER_TEMPLATE = """Report title: {title}
Published: {published_at}

{body}"""

_STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "org_name_raw": {
            "type": "string",
            "description": "The organisation's name exactly as the report names it.",
        },
        "activity": {
            "type": "string",
            "description": "A short factual description of what the organisation did, in your own words.",
        },
        "activity_type": {
            "type": "string",
            "enum": list(enums.ACTIVITY_TYPE),
        },
        "where_raw": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Place names exactly as the text uses them. Empty if the text names none.",
        },
        "happened_on": {
            "type": ["string", "null"],
            "description": "ISO 8601 date (YYYY-MM-DD) if the text states one, else null.",
        },
        "amount": {
            "type": ["number", "null"],
            "description": "The numeric amount as the text states it, or null if none is mentioned.",
        },
        "currency": {
            "type": ["string", "null"],
            "description": "ISO 4217 three-letter currency code, or null if amount is null.",
        },
        "amount_basis": {
            "type": "string",
            "enum": list(enums.AMOUNT_BASIS),
        },
        "quote": {
            "type": "string",
            "description": "The verbatim, at-most-40-word quote from the report text that supports this statement.",
        },
    },
    "required": ["org_name_raw", "activity", "activity_type", "where_raw", "amount_basis", "quote"],
}

STATEMENT_TOOL = {
    "type": "function",
    "function": {
        "name": STATEMENT_TOOL_NAME,
        "description": "Record every organisational disaster-response statement found in this report.",
        "parameters": {
            "type": "object",
            "properties": {
                "statements": {
                    "type": "array",
                    "items": _STATEMENT_SCHEMA,
                }
            },
            "required": ["statements"],
        },
    },
}


@dataclass(frozen=True)
class ReportInput:
    """Everything build_messages() needs from one report row."""

    url: str
    title: str
    body: str
    published_at: str | None = None
    known_districts: tuple[str, ...] = field(default_factory=tuple)


def build_messages(report: ReportInput) -> list[dict[str, str]]:
    """The two-message chat-completion request for one report. No I/O, deterministic."""
    known = ", ".join(report.known_districts) if report.known_districts else "none known for this report"
    system = SYSTEM_PROMPT.format(known_districts=known)
    user = USER_TEMPLATE.format(
        title=report.title,
        published_at=report.published_at or "unknown",
        body=report.body,
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
