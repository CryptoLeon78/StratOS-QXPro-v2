"""PARTE 13: cuentas REAL "Prod" + DEMO "Quarry". El capital inicial
(30.000 EUR) y la fecha de alta (2021-01-04) del enunciado no son campos
de `Account` -- se representan como el primer `EquitySnapshot` de la
cuenta (equity_curve.py), que es de donde `compute_reconciliation` (7.9)
realmente los lee."""

from core.db.models.accounts import Account
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_accounts(session: AsyncSession) -> dict[str, Account]:
    prod = Account(
        name="Prod",
        broker="Darwinex",
        login="stratos-prod-1",
        server="Darwinex-Live",
        currency="EUR",
        is_demo=False,
        is_active=True,
    )
    quarry = Account(
        name="Quarry",
        broker="Darwinex",
        login="stratos-quarry-1",
        server="Darwinex-Demo",
        currency="EUR",
        is_demo=True,
        is_active=True,
    )
    session.add_all([prod, quarry])
    await session.flush()
    return {"prod": prod, "quarry": quarry}
