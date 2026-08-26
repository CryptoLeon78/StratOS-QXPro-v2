"""Test de humo (PARTE 12 G5): los nombres de funcion que el scheduler
encola/ejecuta por cron deben existir tambien en `worker.functions` --
evita el bug real de "el scheduler dispara un nombre que el worker no
tiene registrado" (indetectable en produccion sin este check, arq no
valida esto por si solo)."""

from core.jobs.scheduler import CRON_JOBS, SchedulerSettings
from core.jobs.worker import FUNCTIONS, WorkerSettings


def test_every_cron_job_coroutine_is_registered_in_worker_functions() -> None:
    worker_names = {fn.__name__ for fn in FUNCTIONS}
    # arq antepone "cron:" al nombre de la coroutine (CronJob.name).
    cron_names = {job.name.removeprefix("cron:") for job in CRON_JOBS}
    missing = cron_names - worker_names
    assert not missing, f"cron jobs sin funcion registrada en worker.py: {missing}"


def test_worker_settings_functions_match_module_constant() -> None:
    assert WorkerSettings.functions == FUNCTIONS


def test_scheduler_settings_cron_jobs_match_module_constant() -> None:
    assert SchedulerSettings.cron_jobs == CRON_JOBS


def test_no_duplicate_cron_jobs_for_the_same_coroutine() -> None:
    names = [job.name for job in CRON_JOBS]
    assert len(names) == len(set(names))
