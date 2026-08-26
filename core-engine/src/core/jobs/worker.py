"""Proceso ARQ que CONSUME jobs encolados bajo demanda (p.ej. un boton
"Recalcular ahora" de un router que hace `redis.enqueue_job(...)`).
`docker-compose.yml` (G0) ya fija el nombre exacto de este modulo/clase:
`command: ["arq", "core.jobs.worker.WorkerSettings"]`.

El barrido PERIODICO automatico vive en `scheduler.py` (proceso ARQ
separado, mismo patron de docker-compose) -- ambos procesos ejecutan las
MISMAS funciones `task_*` (jobs/tasks.py), cada uno necesita su propio
`ctx["session_factory"]` (`startup`, reutilizado por los dos)."""

from typing import Any

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config import get_settings
from core.db.base import engine
from core.jobs.tasks import (
    task_evaluate_impulses,
    task_maybe_send_digest,
    task_run_audit_daily,
    task_run_config_drift,
    task_run_correlations,
    task_run_killswitch_sweep,
    task_run_montecarlo_check,
    task_run_semaphore_sweep,
    task_run_ums_downgrade_check,
    task_run_watchdog,
)

FUNCTIONS = [
    task_run_semaphore_sweep,
    task_run_killswitch_sweep,
    task_run_watchdog,
    task_run_correlations,
    task_run_montecarlo_check,
    task_run_audit_daily,
    task_run_ums_downgrade_check,
    task_evaluate_impulses,
    task_run_config_drift,
    task_maybe_send_digest,
]


async def startup(ctx: dict[str, Any]) -> None:
    ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)


class WorkerSettings:
    functions = FUNCTIONS
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
