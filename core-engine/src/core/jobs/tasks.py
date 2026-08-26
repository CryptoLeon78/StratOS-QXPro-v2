"""Wrappers finos de ARQ (jobs/worker.py) sobre core/services/*. Toda la
logica real vive en los servicios, ya probados contra Postgres/Redis reales
-- estas funciones solo resuelven `ctx["session_factory"]`/`ctx["redis"]`
(inyectados por `worker.py::WorkerSettings.on_startup`, o un fake minimo en
tests) y hacen el commit final. `ctx["redis"]` es directamente el cliente
`ArqRedis` que arq ya mantiene (subclase de `redis.asyncio.Redis`, mismo
`.publish()` que usan los servicios) -- no hace falta una conexion aparte."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from core.services.audit import AuditConfig, run_audit_daily
from core.services.config_drift import run_drift_check
from core.services.correlations import CorrelationServiceConfig, run_correlation_job
from core.services.impulses import ImpulseServiceConfig, evaluate_pending_impulses
from core.services.killswitch_sweep import KillSwitchSweepConfig, sweep_portfolio
from core.services.montecarlo import (
    MonteCarloServiceConfig,
    bots_due_for_recalc,
    run_montecarlo_for_bot,
)
from core.services.risk import real_portfolio_equity_curve
from core.services.semaphore_sweep import SemaphoreSweepConfig, sweep_all_bots
from core.services.ums import UmsConfig, check_automatic_downgrade
from core.services.watchdog import WatchdogServiceConfig, run_watchdog_sweep
from core.state_machines.types import KillSwitchConfig, SemaphoreConfig


async def task_run_semaphore_sweep(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await sweep_all_bots(
            session, ctx["redis"], SemaphoreConfig(), SemaphoreSweepConfig(), datetime.now(UTC)
        )
        await session.commit()


async def task_run_killswitch_sweep(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await sweep_portfolio(
            session, ctx["redis"], KillSwitchConfig(), KillSwitchSweepConfig(), datetime.now(UTC)
        )
        await session.commit()


async def task_run_watchdog(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await run_watchdog_sweep(session, ctx["redis"], WatchdogServiceConfig(), datetime.now(UTC))
        await session.commit()


async def task_run_correlations(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await run_correlation_job(
            session, ctx["redis"], CorrelationServiceConfig(), datetime.now(UTC)
        )
        await session.commit()


async def task_run_montecarlo_check(ctx: dict[str, Any]) -> None:
    now = datetime.now(UTC)
    config = MonteCarloServiceConfig()
    async with ctx["session_factory"]() as session:
        for bot in await bots_due_for_recalc(session, config, now):
            await run_montecarlo_for_bot(session, bot, config, now)
        await session.commit()


async def task_run_audit_daily(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await run_audit_daily(session, ctx["redis"], AuditConfig(), datetime.now(UTC))
        await session.commit()


async def task_run_ums_downgrade_check(ctx: dict[str, Any]) -> None:
    now = datetime.now(UTC)
    async with ctx["session_factory"]() as session:
        equity_curve = await real_portfolio_equity_curve(session, now - timedelta(days=7))
        if equity_curve.empty:
            return
        current_equity = Decimal(str(equity_curve.iloc[-1]))
        await check_automatic_downgrade(session, ctx["redis"], UmsConfig(), current_equity, now)
        await session.commit()


async def task_evaluate_impulses(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await evaluate_pending_impulses(session, ImpulseServiceConfig(), datetime.now(UTC))
        await session.commit()


async def task_run_config_drift(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await run_drift_check(session, ctx["redis"], datetime.now(UTC))
        await session.commit()
