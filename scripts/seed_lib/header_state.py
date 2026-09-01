"""Verificacion final del seed (no siembra nada) -- PARTE 13 da el estado
de cabecera como una FOTO puntual con cifras literales exactas (equity
179.642,70, DD 0,4%, 2 alertas...) que este seed, sintetico y aproximado
por diseno (ver ASSUMPTIONS G8), no reproduce al centimo. Lo que SI se
verifica -- via `routers/header.py::header_summary`, el MISMO calculo que
consume el frontend, no uno reimplementado -- son las propiedades
ESTRUCTURALES que cualquier estado de cabecera coherente debe cumplir. Si
alguna falla, el seed aborta ruidosamente (AssertionError) en vez de
dejar datos incoherentes en la base."""

from datetime import datetime

from core.db.enums import SemaphoreState
from core.db.models.accounts import Account, Bot
from core.routers.header import compute_header_summary
from core.services.audit import AuditConfig, compute_reconciliation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def verify_header_state(
    session: AsyncSession,
    account: Account,
    *,
    inject_audit_error: bool,
    as_of: datetime | None = None,
) -> None:
    """Verifica el fixture con su reloj lógico, nunca el reloj productivo.

    El perfil ``full`` está deliberadamente congelado. Por ello su último
    snapshot puede ser anterior al día en que se ejecute CI; evaluar la
    cabecera contra ``datetime.now`` la convertiría artificialmente en una
    curva vacía. El endpoint sigue usando el reloj real: esta inyección se
    limita a la comprobación interna del seed.
    """
    summary = await compute_header_summary(session=session, now=as_of)
    print(
        f"[seed] cabecera: equity={summary.equity_eur} DD={summary.portfolio_dd_pct}% "
        f"KS_L{summary.ks_level} semaforo={summary.global_semaphore} "
        f"pos_abiertas={summary.open_positions} alertas={summary.alerts} "
        f"decisiones_pendientes={summary.pending_decisions} "
        f"MT_conectado={summary.mt_connected} stale={summary.data_stale_seconds}s"
    )

    assert summary.equity_eur > 0, f"equity no positivo: {summary.equity_eur}"
    assert summary.portfolio_dd_pct >= 0, f"DD negativo: {summary.portfolio_dd_pct}"
    assert summary.ks_level == 0, f"kill-switch escalado inesperadamente: L{summary.ks_level}"
    assert summary.open_positions >= 1, "falta la posicion sin SL del escenario (criterio 12)"
    assert summary.alerts >= 1, "cero alertas activas (se esperaba al menos la del P5)"
    assert summary.pending_decisions >= 1, "cero decisiones pendientes (se esperaba Poseidon)"

    poseidon = (
        await session.execute(select(Bot).where(Bot.name == "Poseidón Trend GER40"))
    ).scalar_one()
    assert poseidon.semaphore_state == SemaphoreState.NARANJA, (
        f"Poseidon no esta en NARANJA (criterio 2): {poseidon.semaphore_state}"
    )

    recon = await compute_reconciliation(session, account.id, AuditConfig())
    assert recon is not None, "reconciliacion no calculable (faltan EquitySnapshot)"
    if inject_audit_error:
        assert recon.breached, "se esperaba una discrepancia inyectada (--inject-audit-error)"
    else:
        assert not recon.breached, f"reconciliacion incumplida sin --inject-audit-error: {recon}"

    print("[seed] verificacion de cabecera: OK")
