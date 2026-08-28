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
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from core.models import OrgDatum

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
ChannelType = Literal["donation_page", "bank_transfer_page", "platform_page"]


class Datum(BaseModel):
    """One value with its provenance, or one explicit gap.

    A gap is {"value": null, "is_gap": true, "note": ..., "gap_reason": ...}. Every key is present
    in both cases.

    Every field is required-but-nullable rather than optional-with-a-default, and that is
    deliberate. A default makes the field optional in the generated OpenAPI schema, which tells a
    client the key may be absent - and a missing key and a null value render differently. The
    frontend builds its whole honesty design on "the key is always there", so the contract has to
    promise it rather than merely happen to satisfy it.
    """

    value: Any | None = Field(description="null means no value was found; see gap_reason")
    is_gap: bool = Field(description="true exactly when value is null")
    value_type: ValueType | None = Field(description="how to read value; null for a gap")
    currency: str | None = Field(description="ISO 4217, for money values")
    fiscal_year: str | None = Field(description='e.g. "2024" or "2024/25"')
    scope: MoneyScope | None = Field(description="whether a figure is global or Nepal only")
    source_url: str | None = Field(description="present whenever value is not null")
    retrieved_at: date | None = Field(description="when the source was read")
    quote: str | None = Field(description="verbatim, at most 40 words")
    note: str | None = Field(description="present whenever value is null")
    verification: Verification
    gap_reason: GapReason | None = Field(description="present exactly when value is null")
    channel_type: ChannelType | None = Field(
        description="for a donation_channel datum: what the link asks of a reader. Null elsewhere."
    )
    flood_specific: bool | None = Field(
        description=(
            "for a donation_channel datum: true when the link is this disaster's campaign, false "
            "when it is the organisation's standing donation page. Null elsewhere."
        )
    )


def serialise_datum(row: OrgDatum) -> Datum:
    """The one place an `org_datum` row becomes a `Datum`. Every field is copied straight across,
    never conditionally omitted: a gap keeps `value: null, is_gap: true` plus its `note` and
    `gap_reason`, and a value keeps neither. Nothing else in this codebase may build a `Datum`."""
    return Datum(
        value=row.value,
        is_gap=row.is_gap,
        value_type=row.value_type,
        currency=row.currency,
        fiscal_year=row.fiscal_year,
        scope=row.scope,
        source_url=row.source_url,
        retrieved_at=row.retrieved_at,
        quote=row.quote,
        note=row.note,
        verification=row.verification,
        gap_reason=row.gap_reason,
        channel_type=row.channel_type,
        flood_specific=row.flood_specific,
    )


class DonationChannel(BaseModel):
    """An organisation's official donation page, compactly, for a board row.

    Only ever the organisation's own registrable domain - the loader rejects anything else before
    it reaches the database - and never payment details: a link, not an account number. Null on a
    row means no official channel was found, which the board states rather than hides. The full
    datum, with its note, quote and gap_reason, is on the organisation's own page.
    """

    url: str
    channel_type: ChannelType | None
    verification: Verification
    retrieved_at: date | None
    flood_specific: bool | None = Field(
        description="true when this is the campaign for this disaster rather than a standing page"
    )


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
    quote: str | None = Field(
        default=None,
        description=(
            "verbatim, at most 40 words. Null only on a hand-researched statement, where the fact "
            "came from a structured page rather than a sentence; a statement an LLM extracted "
            "always carries its quote."
        ),
    )
    source: SourceRef


class OrgRef(BaseModel):
    org_id: str
    name_common: str
    org_type: str
    hq_country: str | None = None
    website: str | None = None
    aliases: list[str] = Field(
        default_factory=list,
        description=(
            "other names this organisation is known by. The board's name search is useless without "
            "them: people type NRCS, MSF and WV Nepal, none of which is a substring of the common name."
        ),
    )
    local_script: str | None = Field(
        default=None,
        description='the Devanagari name where one was found; rendered with lang="ne"',
    )


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
    donation_channel: DonationChannel | None = Field(
        default=None,
        description=(
            "the organisation's own official donation page, or null when none was found. Every "
            "row carries this field and it is presented identically for every organisation: it is "
            "a way to act, never a recommendation, and null is stated rather than hidden."
        ),
    )


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
