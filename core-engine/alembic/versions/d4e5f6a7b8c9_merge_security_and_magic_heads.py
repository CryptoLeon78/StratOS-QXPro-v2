"""merge security and magic heads

Revision ID: d4e5f6a7b8c9
Revises: a4b5c6d7e8f9, c3d4e5f6a7b8
"""

from collections.abc import Sequence

revision: str = "d4e5f6a7b8c9"
down_revision: tuple[str, str] = ("a4b5c6d7e8f9", "c3d4e5f6a7b8")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
