"""Fixtures de BBDD DUPLICADAS deliberadamente de `core-engine/tests/conftest.py`
(mismo patron SAVEPOINT, misma creacion de `stratos_test`) -- no son
importables tal cual: viven en el paquete de tests de core-engine, que NO
se expone como API instalable (`[tool.hatch.build.targets.wheel] packages
= ["src/core"]` no incluye `tests/`). Convertir esas fixtures en un plugin
pytest exportable seria mas complejo que mantener esta copia sincronizada
a mano para un unico caso de uso -- si `core-engine/tests/conftest.py`
cambia, actualizar aqui tambien."""

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest_asyncio
from core.config import get_settings
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

TEST_DB_NAME = "stratos_test"
CORE_ENGINE_DIR = (
    Path(__file__).resolve().parents[2] / "core-engine"
)  # .../StratOS-QXPro-v2/core-engine


def _with_db_name(url: str, db_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db_name}"


def _to_asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


@pytest_asyncio.fixture(scope="session")
async def test_database() -> AsyncIterator[dict[str, str]]:
    settings = get_settings()
    admin_dsn = _to_asyncpg_dsn(_with_db_name(settings.database_url, "postgres"))
    owner_url = _with_db_name(settings.database_url, TEST_DB_NAME)
    app_url = _with_db_name(settings.app_database_url, TEST_DB_NAME)

    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            TEST_DB_NAME,
        )
        await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        await conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    finally:
        await conn.close()

    env = {**os.environ, "DATABASE_URL": owner_url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=CORE_ENGINE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic upgrade head failed:\n{result.stderr}"

    yield {"owner_url": owner_url, "app_url": app_url}


@pytest_asyncio.fixture
async def db_connection(test_database: dict[str, str]) -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(test_database["owner_url"])
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            yield conn
        finally:
            await trans.rollback()
    await engine.dispose()
