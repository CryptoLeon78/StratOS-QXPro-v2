"""Wrappers finos de ARQ (jobs/worker.py) sobre core/services/*. Toda la
logica real vive en los servicios, ya probados contra Postgres/Redis reales
-- estas funciones solo resuelven `ctx["session_factory"]`/`ctx["redis"]`
(inyectados por `worker.py::WorkerSettings.on_startup`, o un fake minimo en
tests) y hacen el commit final. `ctx["redis"]` es directamente el cliente
`ArqRedis` que arq ya mantiene (subclase de `redis.asyncio.Redis`, mismo
`.publish()` que usan los servicios) -- no hace falta una conexion aparte."""

import functools
import json
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.db.enums import AlertLevel
from core.metrics import ARQ_JOB_DURATION_SECONDS, ARQ_JOB_FAILURES_TOTAL
from core.notifications.dispatch import dispatch_new_alerts
from core.notifications.telegram import send_telegram_message
from core.services.audit import AuditConfig, run_audit_daily
from core.services.config_drift import run_drift_check
from core.services.correlations import CorrelationServiceConfig, run_mt5_real_correlation_snapshot
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

_DIGEST_HOUR_UTC = 20  # telegram_soft_digest_hour_utc, thresholds.seed.json
_DIGEST_QUEUE_KEY = "telegram:digest:pending"

_TaskFn = Callable[..., Awaitable[None]]


def _instrumented(job_name: str) -> Callable[[_TaskFn], _TaskFn]:
    """arq_job_duration_seconds/arq_job_failures_total (metrics.py, ya
    existen) para cada task_*. `functools.wraps` preserva `__name__` --
    el test de humo worker/scheduler (test_worker_scheduler_smoke.py)
    depende de que `fn.__name__` siga siendo el nombre real de la tarea."""

    def decorator(func: _TaskFn) -> _TaskFn:
        @functools.wraps(func)
        async def wrapper(ctx: dict[str, Any]) -> None:
            start = time.perf_counter()
            try:
                await func(ctx)
            except Exception:
                ARQ_JOB_FAILURES_TOTAL.labels(job_name=job_name).inc()
                raise
            finally:
                ARQ_JOB_DURATION_SECONDS.labels(job_name=job_name).observe(
                    time.perf_counter() - start
                )

        return wrapper

    return decorator


async def _dispatch_new_alerts(session: AsyncSession, redis: Any, run_start: datetime) -> None:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        await dispatch_new_alerts(session, redis, client, settings, run_start)


@_instrumented("task_run_semaphore_sweep")
async def task_run_semaphore_sweep(ctx: dict[str, Any]) -> None:
    run_start = datetime.now(UTC)
    async with ctx["session_factory"]() as session:
        await sweep_all_bots(
            session, ctx["redis"], SemaphoreConfig(), SemaphoreSweepConfig(), run_start
        )
        await session.commit()
        await _dispatch_new_alerts(session, ctx["redis"], run_start)


@_instrumented("task_run_killswitch_sweep")
async def task_run_killswitch_sweep(ctx: dict[str, Any]) -> None:
    run_start = datetime.now(UTC)
    async with ctx["session_factory"]() as session:
        await sweep_portfolio(
            session, ctx["redis"], KillSwitchConfig(), KillSwitchSweepConfig(), run_start
        )
        await session.commit()
        await _dispatch_new_alerts(session, ctx["redis"], run_start)


@_instrumented("task_run_watchdog")
async def task_run_watchdog(ctx: dict[str, Any]) -> None:
    run_start = datetime.now(UTC)
    async with ctx["session_factory"]() as session:
        await run_watchdog_sweep(session, ctx["redis"], WatchdogServiceConfig(), run_start)
        await session.commit()
        await _dispatch_new_alerts(session, ctx["redis"], run_start)


@_instrumented("task_run_correlations")
async def task_run_correlations(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await run_mt5_real_correlation_snapshot(
            session, CorrelationServiceConfig(), datetime.now(UTC)
        )
        await session.commit()


@_instrumented("task_run_montecarlo_check")
async def task_run_montecarlo_check(ctx: dict[str, Any]) -> None:
    now = datetime.now(UTC)
    config = MonteCarloServiceConfig()
    async with ctx["session_factory"]() as session:
        for bot in await bots_due_for_recalc(session, config, now):
            await run_montecarlo_for_bot(session, bot, config, now)
        await session.commit()


@_instrumented("task_run_audit_daily")
async def task_run_audit_daily(ctx: dict[str, Any]) -> None:
    run_start = datetime.now(UTC)
    async with ctx["session_factory"]() as session:
        await run_audit_daily(session, ctx["redis"], AuditConfig(), run_start)
        await session.commit()
        await _dispatch_new_alerts(session, ctx["redis"], run_start)


@_instrumented("task_run_ums_downgrade_check")
async def task_run_ums_downgrade_check(ctx: dict[str, Any]) -> None:
    run_start = datetime.now(UTC)
    async with ctx["session_factory"]() as session:
        equity_curve = await real_portfolio_equity_curve(session, run_start - timedelta(days=7))
        if equity_curve.empty:
            return
        current_equity = Decimal(str(equity_curve.iloc[-1]))
        await check_automatic_downgrade(
            session, ctx["redis"], UmsConfig(), current_equity, run_start
        )
        await session.commit()
        await _dispatch_new_alerts(session, ctx["redis"], run_start)


@_instrumented("task_evaluate_impulses")
async def task_evaluate_impulses(ctx: dict[str, Any]) -> None:
    async with ctx["session_factory"]() as session:
        await evaluate_pending_impulses(session, ImpulseServiceConfig(), datetime.now(UTC))
        await session.commit()


@_instrumented("task_run_config_drift")
async def task_run_config_drift(ctx: dict[str, Any]) -> None:
    run_start = datetime.now(UTC)
    async with ctx["session_factory"]() as session:
        await run_drift_check(session, ctx["redis"], run_start)
        await session.commit()
        await _dispatch_new_alerts(session, ctx["redis"], run_start)


@_instrumented("task_maybe_send_digest")
async def task_maybe_send_digest(ctx: dict[str, Any]) -> None:
    """PARTE 9.4: digest diario de alertas SUAVE encoladas por
    dispatch_alert (telegram:digest:pending) -- se autocomprueba cada hora
    (scheduler.py, cron con minute=0) y solo actua a `_DIGEST_HOUR_UTC`."""
    now = datetime.now(UTC)
    if now.hour != _DIGEST_HOUR_UTC:
        return

    redis = ctx["redis"]
    pending: list[dict[str, Any]] = []
    while True:
        item = await redis.lpop(_DIGEST_QUEUE_KEY)
        if item is None:
            break
        pending.append(json.loads(item))
    if not pending:
        return

    lines = [f"- {p['message']}" for p in pending]
    text = f"Resumen diario de alertas SUAVE ({len(pending)}):\n" + "\n".join(lines)
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        await send_telegram_message(client, settings, text, AlertLevel.SUAVE)
