"""G11: artefactos administrativos auditables y version EA requerida."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7f2c9910c1e"
down_revision: str | None = "3960d7d19b0d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_artifact",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("parser_version", sa.String(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "sha256"),
    )
    op.add_column("bot", sa.Column("ea_required_version", sa.String(), nullable=True))
    op.add_column("baseline", sa.Column("artifact_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_baseline_artifact", "baseline", "import_artifact", ["artifact_id"], ["id"]
    )
    op.add_column("fx_rate", sa.Column("artifact_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_fx_rate_artifact", "fx_rate", "import_artifact", ["artifact_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_fx_rate_artifact", "fx_rate", type_="foreignkey")
    op.drop_column("fx_rate", "artifact_id")
    op.drop_constraint("fk_baseline_artifact", "baseline", type_="foreignkey")
    op.drop_column("baseline", "artifact_id")
    op.drop_column("bot", "ea_required_version")
    op.drop_table("import_artifact")
