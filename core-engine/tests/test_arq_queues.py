"""El scheduler no comparte cola con el worker.

Ambos procesos ARQ apuntan al mismo Redis. Con la cola por defecto, los jobs
de cron que encola el scheduler quedan a la vista del worker, que no los
declara como `cron_jobs` y los descarta: en los logs del worker aparecia
`function 'cron:task_run_killswitch_sweep' not found` cada minuto. El barrido
seguia corriendo en el scheduler, pero nada impedia que el worker se
adelantara y ese barrido concreto se perdiera.

Cada proceso con su cola: el scheduler ejecuta sus crons y el worker atiende
los jobs bajo demanda, sin robarse trabajo.
"""

from __future__ import annotations

from core.jobs.scheduler import SchedulerSettings
from core.jobs.worker import WorkerSettings


def test_scheduler_y_worker_no_comparten_cola() -> None:
    scheduler_queue = getattr(SchedulerSettings, "queue_name", None)
    worker_queue = getattr(WorkerSettings, "queue_name", None)

    assert scheduler_queue is not None, "el scheduler debe declarar su propia cola"
    assert scheduler_queue != worker_queue, (
        "el worker recogeria los jobs de cron del scheduler y los descartaria; "
        f"ambos usan {scheduler_queue!r}"
    )
