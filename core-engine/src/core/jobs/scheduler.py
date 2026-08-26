"""Proceso ARQ que EJECUTA el barrido periodico automatico via `arq.cron`
-- cada `CronJob` invoca su coroutine directamente en este mismo proceso
(no encola nada para `worker.py`). `docker-compose.yml` (G0) ya fija el
nombre exacto: `command: ["arq", "core.jobs.scheduler.SchedulerSettings"]`.

Cadencias propuestas (ASSUMPTIONS G5, PARTE 10.3 solo fija la de
correlaciones -- domingo 06:00 UTC, 7.5 -- y la de Monte Carlo -- mensual +
cada 50 trades, 7.7, aproximada en `bots_due_for_recalc` por un barrido
diario): kill-switch cada 1 min (el mas sensible a tiempo, un DD que
escala rapido no puede esperar), semaforo cada 5 min, watchdog/deriva de
config cada 10-15 min, el resto (auditoria, impulsos, downgrade UMS,
Monte Carlo) diarios/horarios en franjas de baja actividad (madrugada
UTC)."""

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from core.config import get_settings
from core.jobs.tasks import (
    task_evaluate_impulses,
    task_run_audit_daily,
    task_run_config_drift,
    task_run_correlations,
    task_run_killswitch_sweep,
    task_run_montecarlo_check,
    task_run_semaphore_sweep,
    task_run_ums_downgrade_check,
    task_run_watchdog,
)
from core.jobs.worker import startup

CRON_JOBS = [
    cron(task_run_killswitch_sweep, minute=set(range(60)), second=0),
    cron(task_run_semaphore_sweep, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    cron(task_run_watchdog, minute={0, 15, 30, 45}),
    cron(task_run_config_drift, minute={0, 10, 20, 30, 40, 50}),
    cron(task_run_correlations, weekday="sun", hour=6, minute=0),
    cron(task_run_montecarlo_check, hour=3, minute=0),
    cron(task_run_audit_daily, hour=2, minute=0),
    cron(task_run_ums_downgrade_check, minute=0),
    cron(task_evaluate_impulses, hour=4, minute=0),
]


class SchedulerSettings:
    cron_jobs = CRON_JOBS
    on_startup: Any = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
