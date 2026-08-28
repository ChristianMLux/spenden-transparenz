"""The 14 tables.

Two design rules run through all of them:

1. Enums are TEXT with a CHECK built from core.enums. Alembic cannot alter a native Postgres enum
   inside a transaction, and every one of these lists is expected to grow.
2. Provenance is a constraint, not a convention. org_datum physically cannot hold a value without a
   source, or a gap without a reason and a note. A rule enforced only in a loader is a rule the next
   loader forgets.

There is no score, grade or rating column anywhere, and a test asserts that. Verification filters
are SQL over datums; sorting is by recency or name.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core import enums


class Base(DeclarativeBase):
    # ClassVar keeps ruff's mutable-default rule quiet and is what SQLAlchemy expects here anyway:
    # the declarative mapper ignores ClassVar-annotated attributes rather than mapping them.
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict[str, Any]: JSONB,
        datetime: DateTime(timezone=True),
        date: Date,
        Decimal: Numeric,
        str: Text,
    }


def _enum_check(column: str, values: tuple[str, ...], table: str) -> CheckConstraint:
    return CheckConstraint(enums.check_in(column, values), name=f"ck_{table}_{column}")


# The value of response_statement.model for a statement that came from the human research pass
# rather than from a language model. The provenance CHECK on quote keys off it.
HAND_RESEARCH_MODEL = "hand_research"

TIMESTAMP_NOW = func.now()


class IngestionRun(Base):
    """One row per job execution. Every job opens one and closes it, including on exception."""

    __tablename__ = "ingestion_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False, server_default=TIMESTAMP_NOW)
    finished_at: Mapped[datetime | None]
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    rows_skipped: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    git_sha: Mapped[str | None]
    error: Mapped[str | None]

    __table_args__ = (
        _enum_check("status", enums.RUN_STATUS, "ingestion_run"),
        Index("ix_ingestion_run_job_started", "job", "started_at"),
    )


class Source(Base):
    """Where data comes from, with its licence. Rendered on the sources page.

    licence is nullable on purpose: a licence we could not read on the source's own terms page is
    recorded as unknown with a note, never as a guessed licence string.
    """

    __tablename__ = "source"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    licence: Mapped[str | None]
    licence_url: Mapped[str | None]
    licence_note: Mapped[str | None]
    default_verification: Mapped[str] = mapped_column(nullable=False)
    retrieved_at: Mapped[date | None]

    __table_args__ = (_enum_check("default_verification", enums.VERIFICATION, "source"),)


class Organisation(Base):
    """Only the filter axes are columns. Every other fact is an org_datum with its own provenance."""

    __tablename__ = "organisations"

    org_id: Mapped[str] = mapped_column(primary_key=True)
    name_common: Mapped[str] = mapped_column(nullable=False)
    org_type: Mapped[str] = mapped_column(nullable=False)
    hq_country: Mapped[str | None] = mapped_column(String(2))
    hq_city: Mapped[str | None]
    hq_source_url: Mapped[str | None]
    website: Mapped[str | None]
    last_updated: Mapped[date | None]
    research_notes: Mapped[str | None]
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_run.id"))

    __table_args__ = (
        _enum_check("org_type", enums.ORG_TYPE, "organisations"),
        Index("ix_organisations_hq_country", "hq_country"),
        Index("ix_organisations_org_type", "org_type"),
    )


class OrgDatum(Base):
    """One fact with its provenance. The table the whole product rests on."""

    __tablename__ = "org_datum"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.org_id", ondelete="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(nullable=False)

    # SQL NULL means "no value". JSON null would be a value, would make is_gap false, and would then
    # fail the provenance CHECK for lack of a source_url.
    #
    # none_as_null=True is load-bearing, not tidiness: without it SQLAlchemy serialises Python None
    # into the JSON literal 'null' for a JSON/JSONB column, and every gap in the dataset would be
    # stored as a value. Verified against Postgres 16 - the first run of the model tests failed
    # exactly this way.
    value: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    value_type: Mapped[str | None]
    currency: Mapped[str | None] = mapped_column(String(3))
    fiscal_year: Mapped[str | None]
    scope: Mapped[str | None]

    source_url: Mapped[str | None]
    retrieved_at: Mapped[date | None]
    quote: Mapped[str | None]
    note: Mapped[str | None]
    verification: Mapped[str] = mapped_column(nullable=False)
    gap_reason: Mapped[str | None]

    content_hash: Mapped[str] = mapped_column(nullable=False)
    valid_from: Mapped[datetime] = mapped_column(nullable=False, server_default=TIMESTAMP_NOW)
    superseded_at: Mapped[datetime | None]
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_run.id"))

    is_gap: Mapped[bool] = mapped_column(Boolean, Computed("value IS NULL", persisted=True))

    __table_args__ = (
        _enum_check("verification", enums.VERIFICATION, "org_datum"),
        _enum_check("gap_reason", enums.GAP_REASON, "org_datum"),
        _enum_check("value_type", enums.VALUE_TYPE, "org_datum"),
        _enum_check("scope", enums.MONEY_SCOPE, "org_datum"),
        CheckConstraint(
            "(value IS NOT NULL AND source_url IS NOT NULL AND gap_reason IS NULL)"
            " OR (value IS NULL AND note IS NOT NULL AND gap_reason IS NOT NULL)",
            name="ck_org_datum_provenance",
        ),
        # At most one current row per (org, path). History is append-only: a changed value
        # supersedes the old row, it never overwrites it.
        Index(
            "uq_org_datum_current",
            "org_id",
            "path",
            unique=True,
            postgresql_where=text("superseded_at IS NULL"),
        ),
        Index("ix_org_datum_org", "org_id"),
        Index("ix_org_datum_gap", "is_gap"),
    )


class OrgAlias(Base):
    """Makes extraction joinable: "WV Nepal" -> world-vision-nepal.

    alias_norm is unique across all organisations. Two organisations claiming the same normalised
    alias is a research question, not something a loader should silently pick a winner for.
    """

    __tablename__ = "org_alias"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alias_norm: Mapped[str] = mapped_column(nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.org_id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str | None]

    __table_args__ = (
        UniqueConstraint("alias_norm", name="uq_org_alias_norm"),
        _enum_check("kind", enums.ALIAS_KIND, "org_alias"),
        Index("ix_org_alias_org", "org_id"),
    )


class OrgRegistration(Base):
    """A register entry. A row with identifier NULL is kept: "the register did not answer" is the
    most honest line on an organisation page, and deleting it would hide the gap."""

    __tablename__ = "org_registration"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.org_id", ondelete="CASCADE"), nullable=False)
    registry: Mapped[str] = mapped_column(nullable=False)
    identifier: Mapped[str | None]
    url: Mapped[str | None]
    status: Mapped[str | None]
    retrieved_at: Mapped[date | None]
    verification: Mapped[str] = mapped_column(nullable=False)
    note: Mapped[str | None]
    gap_reason: Mapped[str | None]
    content_hash: Mapped[str] = mapped_column(nullable=False)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_run.id"))

    __table_args__ = (
        _enum_check("registry", enums.REGISTRY, "org_registration"),
        _enum_check("verification", enums.VERIFICATION, "org_registration"),
        _enum_check("gap_reason", enums.GAP_REASON, "org_registration"),
        UniqueConstraint("org_id", "registry", "content_hash", name="uq_org_registration_content"),
        Index("ix_org_registration_org", "org_id"),
    )


class OrgWarning(Base):
    """Public warnings, listed neutrally with a source. Never a reason to hide an organisation."""

    __tablename__ = "org_warning"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.org_id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    source_url: Mapped[str] = mapped_column(nullable=False)
    occurred_on: Mapped[date | None]
    note: Mapped[str] = mapped_column(nullable=False)
    retrieved_at: Mapped[date | None]
    content_hash: Mapped[str] = mapped_column(nullable=False)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_run.id"))

    __table_args__ = (
        _enum_check("type", enums.WARNING_TYPE, "org_warning"),
        UniqueConstraint("org_id", "content_hash", name="uq_org_warning_content"),
    )


class Disaster(Base):
    __tablename__ = "disaster"

    glide_id: Mapped[str] = mapped_column(primary_key=True)
    reliefweb_id: Mapped[str | None]
    name: Mapped[str] = mapped_column(nullable=False)
    country_iso3: Mapped[str | None] = mapped_column(String(3))
    started_on: Mapped[date | None]
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    source_url: Mapped[str | None]
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_run.id"))

    __table_args__ = (UniqueConstraint("reliefweb_id", name="uq_disaster_reliefweb_id"),)


class District(Base):
    """The 77 Nepali admin2 units from the HAPI common operational dataset."""

    __tablename__ = "district"

    code: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    admin1_code: Mapped[str] = mapped_column(nullable=False)
    admin1_name: Mapped[str] = mapped_column(nullable=False)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("source.id"))

    __table_args__ = (
        CheckConstraint(r"code ~ '^NP[0-9]{4}$'", name="ck_district_code_format"),
        Index("ix_district_admin1", "admin1_code"),
    )


class DistrictAlias(Base):
    """Settlement and spelling variants: timure -> NP0301. Every alias comes from a source in the
    dataset, never from general knowledge."""

    __tablename__ = "district_alias"

    alias_norm: Mapped[str] = mapped_column(primary_key=True)
    district_code: Mapped[str] = mapped_column(ForeignKey("district.code"), nullable=False)
    kind: Mapped[str | None]
    source_url: Mapped[str | None]

    __table_args__ = (
        _enum_check("kind", enums.ALIAS_KIND, "district_alias"),
        Index("ix_district_alias_district", "district_code"),
    )


class Report(Base):
    """A ReliefWeb update. body_text is third-party copyright: stored for extraction, never served.

    What ships is the quote plus the link. A test greps every response model for this column name.
    """

    __tablename__ = "report"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str | None]
    format: Mapped[str | None]
    published_at: Mapped[datetime | None]
    disaster_glide_id: Mapped[str | None] = mapped_column(ForeignKey("disaster.glide_id"))

    body_text: Mapped[str | None]
    body_sha256: Mapped[str | None]
    body_fetched_at: Mapped[datetime | None]

    extraction_attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    last_extraction_error: Mapped[str | None]
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_run.id"))

    __table_args__ = (
        UniqueConstraint("url", name="uq_report_url"),
        Index("ix_report_disaster_published", "disaster_glide_id", "published_at"),
        Index("ix_report_body_sha256", "body_sha256"),
    )


class ReportSource(Base):
    """The publishers of a report, split out of the listing metadata."""

    __tablename__ = "report_source"

    report_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("report.id", ondelete="CASCADE"), primary_key=True)
    publisher: Mapped[str] = mapped_column(primary_key=True)


class ResponseStatement(Base):
    """One claim extracted from one report: org x activity x place x date x verbatim quote.

    org_id is nullable on purpose. An organisation that is named but not identified stays visible
    rather than being dropped, because "we do not know who this is" is information.
    """

    __tablename__ = "response_statement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("report.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[str | None] = mapped_column(ForeignKey("organisations.org_id"))
    org_name_raw: Mapped[str] = mapped_column(nullable=False)

    activity: Mapped[str] = mapped_column(nullable=False)
    activity_type: Mapped[str] = mapped_column(nullable=False)
    where_raw: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    happened_on: Mapped[date | None]
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    # What the amount is: an appeal target, a pledge, money released, or money actually paid
    # out. Defaults to "reported", which claims nothing.
    amount_basis: Mapped[str] = mapped_column(nullable=False, server_default=text("'reported'"))

    # Nullable only for hand-researched statements; the CHECK below enforces that. A claim an
    # LLM extracted must always carry the sentence it came from.
    quote: Mapped[str | None]
    quote_offset: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    verification: Mapped[str] = mapped_column(nullable=False)

    model: Mapped[str] = mapped_column(nullable=False)
    prompt_version: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    content_hash: Mapped[str] = mapped_column(nullable=False)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_run.id"))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=TIMESTAMP_NOW)

    __table_args__ = (
        _enum_check("activity_type", enums.ACTIVITY_TYPE, "response_statement"),
        _enum_check("verification", enums.VERIFICATION, "response_statement"),
        _enum_check("amount_basis", enums.AMOUNT_BASIS, "response_statement"),
        _enum_check("status", enums.STATEMENT_STATUS, "response_statement"),
        UniqueConstraint("report_id", "content_hash", name="uq_response_statement_content"),
        # The 40-word rule is a copyright boundary, so the database keeps it too.
        CheckConstraint(
            r"quote IS NULL OR array_length(regexp_split_to_array(btrim(quote), '\s+'), 1) <= 40",
            name="ck_response_statement_quote_words",
        ),
        # A quote may only be absent on a hand-researched statement, where the fact came from a
        # structured page rather than a sentence. Anything a model produced must show its evidence.
        CheckConstraint(
            f"quote IS NOT NULL OR model = '{HAND_RESEARCH_MODEL}'",
            name="ck_response_statement_quote_required_for_extracted",
        ),
        # A bare number with no currency cannot be rendered honestly.
        CheckConstraint("amount IS NULL OR currency IS NOT NULL", name="ck_response_statement_amount_currency"),
        Index("ix_response_statement_org", "org_id"),
        Index("ix_response_statement_report", "report_id"),
        Index("ix_response_statement_status", "status"),
    )


class StatementDistrict(Base):
    """Where a statement happened, and how we know.

    "the organisation said Rasuwa" (stated) and "the report was about Rasuwa" (inherited) are
    different claims, so the distinction survives all the way to the API.
    """

    __tablename__ = "statement_district"

    statement_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("response_statement.id", ondelete="CASCADE"), primary_key=True
    )
    district_code: Mapped[str] = mapped_column(ForeignKey("district.code"), primary_key=True)
    resolution: Mapped[str] = mapped_column(nullable=False)

    __table_args__ = (
        _enum_check("resolution", enums.DISTRICT_RESOLUTION, "statement_district"),
        Index("ix_statement_district_district", "district_code"),
    )
