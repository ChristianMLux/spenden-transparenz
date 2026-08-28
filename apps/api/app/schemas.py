"""Response models. This file is the contract the web team generates its types from.

Two rules shape every model here:

1. Every provenance-carrying value serialises as the same `Datum` object, and a gap keeps every
   key. A missing key and a null value read completely differently in a frontend, and "not found"
   has to be as renderable as a value.
2. `report.body_text` never appears. What ships is the quote plus the link.

There is no score, grade, rank or rating field, and no sort option that orders by verification:
sorting by how deeply we researched an organisation would rank organisations.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

Verification = Literal[
    "self_reported",
    "register_confirmed",
    "externally_audited",
    "third_party_reported",
    "unverified",
]
GapReason = Literal["not_searched", "searched_not_found", "source_unreachable", "not_public"]
ValueType = Literal["string", "integer", "number", "boolean", "money", "date"]
MoneyScope = Literal["global", "nepal_only", "unknown"]
DistrictResolution = Literal["stated", "inherited_from_report"]
AmountBasis = Literal["reported", "appeal", "pledged", "raised", "released", "disbursed"]


class Datum(BaseModel):
    """One value with its provenance, or one explicit gap.

    A gap is {"value": null, "is_gap": true, "note": ..., "gap_reason": ...}. Every key is present
    in both cases.
    """

    value: Any | None = Field(default=None, description="null means no value was found; see gap_reason")
    is_gap: bool = Field(description="true exactly when value is null")
    value_type: ValueType | None = None
    currency: str | None = Field(default=None, description="ISO 4217, for money values")
    fiscal_year: str | None = Field(default=None, description='e.g. "2024" or "2024/25"')
    scope: MoneyScope | None = Field(default=None, description="whether a figure is global or Nepal only")
    source_url: str | None = Field(default=None, description="present whenever value is not null")
    retrieved_at: date | None = None
    quote: str | None = Field(default=None, description="verbatim, at most 40 words")
    note: str | None = Field(default=None, description="present whenever value is null")
    verification: Verification
    gap_reason: GapReason | None = Field(default=None, description="present exactly when value is null")


class SourceRef(BaseModel):
    """Where a statement came from. Carries the link, never the article text."""

    url: str
    publisher: str | None = None
    published_at: datetime | None = None
    verification: Verification


class DistrictRef(BaseModel):
    code: str = Field(pattern=r"^NP\d{4}$", examples=["NP0329"])
    name: str
    resolution: DistrictResolution = Field(
        description='"stated" = the organisation named this place; "inherited_from_report" = the report was about it'
    )


class StatementOut(BaseModel):
    id: int
    activity: str
    activity_type: str
    districts: list[DistrictRef] = []
    happened_on: date | None = None
    amount: Decimal | None = Field(default=None, description="only set when the quote contains the figure")
    currency: str | None = None
    amount_basis: AmountBasis = Field(
        default="reported",
        description=(
            "what the amount is: an appeal target, a pledge, money raised, money released, or money "
            "actually paid out. Never render a bare figure without it - a pledge and a payment are "
            "different claims. 'reported' claims nothing."
        ),
    )
    quote: str = Field(description="verbatim, at most 40 words")
    source: SourceRef


class OrgRef(BaseModel):
    org_id: str
    name_common: str
    org_type: str
    hq_country: str | None = None
    website: str | None = None


class ResponderCounts(BaseModel):
    statements: int
    districts: int


class ResponderFlags(BaseModel):
    """Facts about what exists, never a judgement about the organisation."""

    has_register_confirmed: bool
    has_audited_financials: bool
    has_warnings: bool


class ResponderItem(BaseModel):
    """One row of the response board.

    org is null when an organisation was named in a report but could not be identified. That row
    stays visible: "we do not know who this is" is information, not a reason to drop it.
    """

    org: OrgRef | None = None
    org_name_raw: str
    statements: list[StatementOut] = []
    counts: ResponderCounts
    flags: ResponderFlags


class DisasterOut(BaseModel):
    glide_id: str = Field(examples=["ff-2026-000162-npl"])
    reliefweb_id: str | None = None
    name: str
    country_iso3: str | None = None
    started_on: date | None = None
    is_active: bool
    source_url: str | None = None


class RegistrationOut(BaseModel):
    """A row with identifier null stays in the response. "The register did not answer" is often
    the most honest line on an organisation page."""

    registry: str
    identifier: str | None = None
    url: str | None = None
    status: str | None = None
    retrieved_at: date | None = None
    verification: Verification
    note: str | None = None
    gap_reason: GapReason | None = None


class WarningOut(BaseModel):
    type: str
    source_url: str
    occurred_on: date | None = None
    note: str
    retrieved_at: date | None = None


class OrgDetail(BaseModel):
    org_id: str
    name_common: str
    org_type: str
    hq_country: str | None = None
    hq_city: str | None = None
    website: str | None = None
    last_updated: date | None = None
    research_notes: str | None = None
    aliases: list[str] = []
    registrations: list[RegistrationOut] = []
    warnings: list[WarningOut] = []
    statements: list[StatementOut] = []
    data: dict[str, Datum] = Field(
        default_factory=dict,
        description="every datum by its JSON path, gaps included, e.g. financial_transparency.income",
    )
    data_gaps: list[str] = Field(default_factory=list, description="paths that stayed empty after a real search")


class DatumHistoryEntry(BaseModel):
    datum: Datum
    valid_from: datetime
    superseded_at: datetime | None = None


class DistrictOut(BaseModel):
    code: str = Field(pattern=r"^NP\d{4}$")
    name: str
    admin1_code: str
    admin1_name: str


class SourceOut(BaseModel):
    id: str
    name: str
    url: str
    licence: str | None = Field(default=None, description="null when the licence could not be verified")
    licence_url: str | None = None
    licence_note: str | None = None
    default_verification: Verification
    retrieved_at: date | None = None


class EnumsOut(BaseModel):
    """Served from core.enums so the frontend never hardcodes a list."""

    enums: dict[str, list[str]]


class FreshnessEntry(BaseModel):
    job: str
    last_success_at: datetime | None = None
    rows_written: int | None = None


class FreshnessOut(BaseModel):
    generated_at: datetime
    jobs: list[FreshnessEntry] = []


class RunOut(BaseModel):
    id: str
    job: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    rows_written: int
    rows_skipped: int
    rows_rejected: int
    cost_usd: Decimal | None = None
    git_sha: str | None = None
    error: str | None = None


class AcceptedOut(BaseModel):
    accepted: bool
    job: str
    run_id: str | None = None
