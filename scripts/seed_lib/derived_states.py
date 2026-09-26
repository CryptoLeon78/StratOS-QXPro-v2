"""PARTE 13/16: invoca los sweeps REALES de core-engine (`services/*`)
sobre los datos crudos ya sembrados -- ningun estado derivado
(`semaphore_state`, `verdict`, `KillSwitchEvent`, `Alert`, `Decision`,
`CorrelationMatrix.is_redundant_pair`, `ImpulseLog.status=CLOSED`) se
escribe a mano en ningun otro modulo de `seed_lib`. Mismo principio que
gobierna todo G8: "estados derivados, no forzados".

Mismos wrappers y misma configuracion por defecto que `core/jobs/tasks.py`
(los jobs ARQ reales) -- se llaman una vez, sincronos, en vez de por cron,
pero es LITERALMENTE el mismo codigo de produccion. No se invoca
`_dispatch_new_alerts` (Telegram): el seed puebla estado, no dispara
notificaciones a un bot real sin token de desarrollo.

Excepcion documentada: el gate de pipeline NO usa
`services/pipeline_gate.py::evaluate_and_persist` -- esa funcion
RE-DERIVA profit_factor/expectancy_r/sharpe/... desde `Trade.bot_id ==
candidate.bot_id`, pero los candidatos de cantera (`bots_pipeline.py`) NO
tienen trades reales (solo sus metricas ya sembradas como literales de
PARTE 13). Usar `evaluate_and_persist` tal cual pondria esas metricas a
cero. Se invoca el mismo par de funciones puras que usa
`evaluate_and_persist` por debajo (`evaluate_pipeline_gate` +
`apply_pipeline_gate`, ambas de `state_machines/pipeline.py`, G3) pero
alimentadas con los campos YA sembrados del `PipelineCandidate`, no
re-consultados de `Trade` -- el veredicto sigue siendo 100% derivado por
la logica real, solo cambia de donde vienen sus metricas de entrada."""

from datetime import datetime

from core.db.models.pipeline import PipelineCandidate
from core.services.audit import AuditConfig, run_audit_daily
from core.services.correlations import (
    CorrelationServiceConfig,
    run_correlation_job,
    run_mt5_real_correlation_snapshot,
)
from core.services.impulses import ImpulseServiceConfig, evaluate_pending_impulses
from core.services.killswitch_sweep import KillSwitchSweepConfig, sweep_portfolio
from core.services.semaphore_sweep import SemaphoreSweepConfig, sweep_all_bots
from core.services.watchdog import WatchdogServiceConfig, run_watchdog_sweep
from core.state_machines.pipeline import apply_pipeline_gate, evaluate_pipeline_gate
from core.state_machines.types import (
    KillSwitchConfig,
    PipelineGateConfig,
    PipelineGateMetrics,
    SemaphoreConfig,
)
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def sweep_pipeline_gate(
    session: AsyncSession, redis: Redis, config: PipelineGateConfig
) -> int:
    candidates = (await session.execute(select(PipelineCandidate))).scalars().all()
    for candidate in candidates:
        metrics = PipelineGateMetrics(
            profit_factor=candidate.profit_factor or 0.0,
            expectancy_r=candidate.expectancy_r or 0.0,
            sharpe=candidate.sharpe or 0.0,
            max_dd_pct=float(candidate.max_dd_pct) if candidate.max_dd_pct is not None else 0.0,
            oos_trades=candidate.oos_trades,
            incubation_days=candidate.incubation_days,
            trades_per_week=candidate.trades_per_week or 0.0,
        )
        result = evaluate_pipeline_gate(metrics, config, sizing_cap_breach=False)
        await apply_pipeline_gate(session, redis, candidate, result)
    return len(candidates)


async def run_all_sweeps(session: AsyncSession, redis: Redis, now: datetime) -> None:
    """Orden: correlaciones/semaforo/kill-switch/watchdog/auditoria/
    impulsos/gate -- ninguno depende del resultado de otro salvo que todos
    necesitan los datos crudos (trades/equity/escenarios) ya commiteados
    antes de llamar a esta funcion."""
    # Dos escrituras a proposito. `run_correlation_job` alimenta la matriz
    # legacy que aun consultan partes del dominio; el snapshot sellado es lo
    # que leen hoy Portfolio y `compute_portfolio_contribution`, y es lo que
    # hace el barrido real (`task_run_correlations`). Sembrando solo el
    # primero, la pestana Portfolio salia sin matriz ni media.
    await run_correlation_job(session, redis, CorrelationServiceConfig(), now)
    await session.commit()

    await run_mt5_real_correlation_snapshot(session, CorrelationServiceConfig(), now)
    await session.commit()

    await sweep_all_bots(session, redis, SemaphoreConfig(), SemaphoreSweepConfig(), now)
    await session.commit()

    await sweep_portfolio(session, redis, KillSwitchConfig(), KillSwitchSweepConfig(), now)
    await session.commit()

    await run_watchdog_sweep(session, redis, WatchdogServiceConfig(), now)
    await session.commit()

    await run_audit_daily(session, redis, AuditConfig(), now)
    await session.commit()

    await evaluate_pending_impulses(session, ImpulseServiceConfig(), now)
    await session.commit()

    await sweep_pipeline_gate(session, redis, PipelineGateConfig())
    await session.commit()
