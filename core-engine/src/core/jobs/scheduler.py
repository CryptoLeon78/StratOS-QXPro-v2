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
from core.jobs.worker import startup

# `WorkerCoroutine` (arq.typing) exige el atributo `__qualname__: str` ademas
# de `__call__` -- ningun valor cuyo tipo estatico se exprese como
# `Callable[...]` (ni siquiera via ParamSpec) lo satisface estructuralmente
# para mypy, solo una `def` literal. `task_*` (jobs/tasks.py) esta envuelta
# por `_instrumented()` precisamente con ese tipo de retorno, de ahi el
# `type: ignore` -- en runtime `functools.wraps` preserva `__qualname__` sin
# problema (ver test_instrumented_task_preserves_function_name).
CRON_JOBS = [
    cron(task_run_killswitch_sweep, minute=set(range(60)), second=0),  # type: ignore[arg-type]
    cron(
        task_run_semaphore_sweep,  # type: ignore[arg-type]
        minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
    ),
    cron(task_run_watchdog, minute={0, 15, 30, 45}),  # type: ignore[arg-type]
    cron(task_run_config_drift, minute={0, 10, 20, 30, 40, 50}),  # type: ignore[arg-type]
    cron(task_run_correlations, weekday="sun", hour=6, minute=0),  # type: ignore[arg-type]
    cron(task_run_montecarlo_check, hour=3, minute=0),  # type: ignore[arg-type]
    cron(task_run_audit_daily, hour=2, minute=0),  # type: ignore[arg-type]
    cron(task_run_ums_downgrade_check, minute=0),  # type: ignore[arg-type]
    cron(task_evaluate_impulses, hour=4, minute=0),  # type: ignore[arg-type]
    # PARTE 9.4: digest SUAVE diario -- se autocomprueba cada hora, solo
    # actua a la hora configurada (telegram_soft_digest_hour_utc).
    cron(task_maybe_send_digest, minute=0),  # type: ignore[arg-type]
]


class SchedulerSettings:
    # Cola propia: con la de por defecto, el worker -- que apunta al mismo
    # Redis y no declara estos `cron_jobs` -- ve los jobs de cron encolados
    # aqui y los descarta (`function 'cron:task_...' not found` cada minuto en
    # sus logs). El barrido seguia corriendo en este proceso, pero nada impedia
    # que el worker se adelantara y ese barrido concreto se perdiera.
    queue_name = "arq:scheduler"
    cron_jobs = CRON_JOBS
    on_startup: Any = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
