"""coordination joins the activity types

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-28

Schema v0.4 added "coordination" to core.enums.ACTIVITY_TYPE and wrote it into two records
(mercy-corps and community-self-reliance-centre, both "coordinating with authorities or
partners"), but the CHECK constraint in the database still carried the original fifteen values.
ingest_orgs would have failed with a CheckViolationError on those two rows.

This is the third time in this project that a changed CHECK expression slipped past autogenerate,
and the second time I have been the one to miss it after writing the warning down. Alembic diffs
whether a constraint exists, not what its expression says, so every enum change needs a hand-
written drop-and-recreate. `test_no_enum_check_has_drifted_from_the_models` now compares every
CHECK in a migrated database against the models and fails on any difference, so the next one is
caught by the suite rather than by a job crashing on real data.
"""

from collections.abc import Sequence

from alembic import op

from core import enums

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = "ck_response_statement_activity_type"
TABLE = "response_statement"

# The fifteen values before coordination was added.
PREVIOUS = tuple(value for value in enums.ACTIVITY_TYPE if value != "coordination")


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE, enums.check_in("activity_type", enums.ACTIVITY_TYPE))


def downgrade() -> None:
    # A statement classified as coordination has no equivalent in the narrower vocabulary, and
    # leaving one behind would fail the recreated CHECK. "other" claims nothing, which is the
    # honest reading of a value the schema can no longer express.
    op.execute(f"UPDATE {TABLE} SET activity_type = 'other' WHERE activity_type = 'coordination'")  # noqa: S608
    op.drop_constraint(CONSTRAINT, TABLE, type_="check")
    op.create_check_constraint(CONSTRAINT, TABLE, enums.check_in("activity_type", PREVIOUS))
