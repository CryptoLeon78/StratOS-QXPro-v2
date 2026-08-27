"""PARTE 13: `--inject-audit-error` (0,02%). Perturba el ULTIMO
`EquitySnapshot.balance` de la cuenta REAL para que
`services/audit.py::compute_reconciliation` (leido por `run_audit_daily`,
derived_states.py) deje de cuadrar -- criterio de aceptacion 6: "seed
limpio 0,00% / --inject-audit-error -> CRITICA". Debe correr ANTES de
`run_all_sweeps` (el propio `run_audit_daily` es quien crea la `Alert`
CRITICA real, no se escribe a mano aqui)."""

from core.db.models.accounts import Account
from core.db.models.market import EquitySnapshot
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# AuditConfig.discrepancy_tolerance=0.0001 (0,01%, services/audit.py) --
# un delta fijo bien por encima de ese umbral relativo a un equity final
# de ~80-180k€ (ver ASSUMPTIONS G8): no se persigue el 0,02% exacto de
# PARTE 13, solo que supere el umbral real de forma inequivoca.
INJECTED_DELTA_EUR = 100


async def inject_audit_error(session: AsyncSession, account: Account) -> None:
    last_ts = (
        await session.execute(
            select(EquitySnapshot.ts)
            .where(EquitySnapshot.account_id == account.id)
            .order_by(EquitySnapshot.ts.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if last_ts is None:
        return

    await session.execute(
        update(EquitySnapshot)
        .where(EquitySnapshot.account_id == account.id, EquitySnapshot.ts == last_ts)
        .values(balance=EquitySnapshot.balance + INJECTED_DELTA_EUR)
    )
