"""account login unique

Revision ID: 0c2dfc843cea
Revises: c78dfdc32060
Create Date: 2026-08-27 21:34:36.692751

Cierra docs/backlog.md (encontrado en G4, `ingest/accounts.py::resolve_account`):
sin UNIQUE, un seed con logins duplicados haria que `scalar_one_or_none()`
lanzara MultipleResultsFound (500) en vez de fallar limpio. Verificado 0
duplicados en el seed actual antes de aplicar (sin necesidad de dedup).

El --autogenerate original tambien detecto (ruido, eliminado a mano, mismo
patron documentado en e215b505cf56): un create_foreign_key duplicado de
fk_bot_baseline_id (use_alter, ya existe desde la 0001) y 3 drop_index sobre
indices que TimescaleDB crea el solo al convertir equity_snapshot/
heartbeat_log/trade en hypertables (no declarados por el modelo SQLAlchemy).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c2dfc843cea"
down_revision: Union[str, None] = "c78dfdc32060"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_account_login", "account", ["login"])


def downgrade() -> None:
    op.drop_constraint("uq_account_login", "account", type_="unique")
