"""G11: historial real append-only del pipeline, sin backfill ficticio."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f99b5d11e82e"
down_revision: str | None = "a7f2c9910c1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_phase_transition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id", sa.Integer(), sa.ForeignKey("pipeline_candidate.id"), nullable=False
        ),
        sa.Column(
            "from_phase",
            postgresql.ENUM(
                "F1",
                "F2",
                "F3",
                "F4",
                "F5",
                "F6",
                "F7",
                "PRODUCCION",
                "CEMENTERIO",
                name="pipeline_phase",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_phase",
            postgresql.ENUM(
                "F1",
                "F2",
                "F3",
                "F4",
                "F5",
                "F6",
                "F7",
                "PRODUCCION",
                "CEMENTERIO",
                name="pipeline_phase",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "actor",
            postgresql.ENUM("SYSTEM", "HUMAN", name="actor_type", create_type=False),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_pipeline_phase_transition_candidate_at",
        "pipeline_phase_transition",
        ["candidate_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pipeline_phase_transition_candidate_at", table_name="pipeline_phase_transition"
    )
    op.drop_table("pipeline_phase_transition")
