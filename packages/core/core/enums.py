"""Enum value sets.

Postgres stores these as TEXT with a CHECK constraint, never as a native enum type: Alembic cannot
alter a native enum inside a transaction, and every one of these lists is expected to grow.

This module is the single source. Models build their CHECK expressions from it, migrations copy the
expression it produces, and /v1/meta/enums serves it, so the frontend never hardcodes a list.
"""

from __future__ import annotations

ORG_TYPE = (
    "un_agency",
    "red_cross_movement",
    "ingo",
    "national_ngo",
    "community_org",
    "diaspora_charity",
    "foundation",
    "government",
    "platform",
    "alliance",
    "unknown",
)

VERIFICATION = (
    "self_reported",
    "register_confirmed",
    "externally_audited",
    "third_party_reported",
    "unverified",
)

# Why a value is missing. Only meaningful when the value is NULL. Without this distinction,
# "we did not look", "we looked and found nothing", "the register did not answer" and
# "the register says it does not publish this" all render as the same empty cell.
GAP_REASON = ("not_searched", "searched_not_found", "source_unreachable", "not_public")

REGISTRY = (
    "NP_SWC",
    "NP_DAO",
    "NP_CDO",
    "UK_CC",
    "UK_OSCR",
    "US_IRS",
    "DE_VEREINSREGISTER",
    "DE_DZI",
    "DE_ITZ",
    "CH_ZEWO",
    "AT_OSGS",
    "IATI",
    "UN",
    "OTHER",
)

WARNING_TYPE = (
    "regulator_inquiry",
    "fraud_allegation",
    "watchdog_alert",
    "delisting",
    "sanction",
    "media_report",
    "other",
)

PRESENCE_MODE = ("own_staff", "partners", "both", "none", "unknown")

VALUE_TYPE = ("string", "integer", "number", "boolean", "money", "date")

MONEY_SCOPE = ("global", "nepal_only", "unknown")

ACTIVITY_TYPE = (
    "relief_distribution",
    "search_and_rescue",
    "medical",
    "shelter",
    "wash",
    "cash_assistance",
    "food",
    "logistics",
    "assessment",
    "appeal_launched",
    "funding_pledged",
    "presence_declared",
    "staff_deployed",
    "needs_statement",
    "other",
)

# What an amount actually is. "Pledged" and "paid" are different claims, and the pilot data
# contains zero disbursed amounts - which is exactly why the enum has to be able to say it.
# Derive this from the activity sentence, never from the note: notes routinely read "not confirmed
# disbursed" or "amount is a pledge, not a confirmed disbursement", so note-matching would label
# pledges as payments.
AMOUNT_BASIS = ("reported", "appeal", "pledged", "raised", "released", "disbursed")

STATEMENT_STATUS = ("auto", "needs_review", "approved", "rejected_unverbatim")

DISTRICT_RESOLUTION = ("stated", "inherited_from_report")

ALIAS_KIND = ("acronym", "local_script", "former_name", "misspelling", "other")

# "queued" is what the admin endpoint writes. The API never runs a job in-process: it records
# the request and the pipeline service drains queued runs on its next tick. That keeps the API
# read-only in practice and keeps the LLM key out of the API service entirely.
RUN_STATUS = ("queued", "running", "succeeded", "failed")

ALL_ENUMS: dict[str, tuple[str, ...]] = {
    "org_type": ORG_TYPE,
    "verification": VERIFICATION,
    "gap_reason": GAP_REASON,
    "registry": REGISTRY,
    "warning_type": WARNING_TYPE,
    "presence_mode": PRESENCE_MODE,
    "value_type": VALUE_TYPE,
    "money_scope": MONEY_SCOPE,
    "activity_type": ACTIVITY_TYPE,
    "amount_basis": AMOUNT_BASIS,
    "statement_status": STATEMENT_STATUS,
    "district_resolution": DISTRICT_RESOLUTION,
    "alias_kind": ALIAS_KIND,
    "run_status": RUN_STATUS,
}


def check_in(column: str, values: tuple[str, ...]) -> str:
    """SQL boolean expression for a TEXT+CHECK enum column.

    NULL is deliberately allowed: a CHECK whose expression evaluates to UNKNOWN is satisfied, so a
    nullable enum column needs no special case. Nullability is decided by the column, not here.

    Both arguments are module constants. No caller data is ever interpolated.
    """
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"
