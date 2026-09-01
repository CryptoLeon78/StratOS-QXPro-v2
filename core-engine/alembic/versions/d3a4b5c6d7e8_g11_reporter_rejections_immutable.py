"""G11: rechazos del reporter e inmutabilidad física de execution_fill."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3a4b5c6d7e8"
down_revision: str | None = "c2e8d801f42b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "execution_fill",
        sa.Column("status", sa.String(), nullable=False, server_default="FILLED"),
    )
    op.add_column("execution_fill", sa.Column("rejection_reason", sa.String(), nullable=True))
    op.alter_column("execution_fill", "executed_price", nullable=True)
    op.create_check_constraint(
        "ck_execution_fill_status", "execution_fill", "status IN ('FILLED', 'REJECTED')"
    )
    op.execute("REVOKE UPDATE, DELETE ON execution_fill FROM stratos_app")
    op.execute(
        """
        CREATE FUNCTION prevent_execution_fill_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'execution_fill es append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER execution_fill_append_only
        BEFORE UPDATE OR DELETE ON execution_fill
        FOR EACH ROW EXECUTE FUNCTION prevent_execution_fill_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER execution_fill_append_only ON execution_fill")
    op.execute("DROP FUNCTION prevent_execution_fill_mutation()")
    op.drop_constraint("ck_execution_fill_status", "execution_fill", type_="check")
    op.alter_column("execution_fill", "executed_price", nullable=False)
    op.drop_column("execution_fill", "rejection_reason")
    op.drop_column("execution_fill", "status")
    op.execute("GRANT UPDATE, DELETE ON execution_fill TO stratos_app")
