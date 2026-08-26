"""Fixtures async de test (PARTE 12 G1). `stratos_test` se crea/migra una
vez por sesion de pytest; cada test corre en un SAVEPOINT que se deshace al
terminar (no ensucia entre tests). Migracion vía subproceso `alembic` con
DATABASE_URL sobreescrito en el entorno: `env.py` siempre lee
`get_settings().database_url` (cacheado con `lru_cache`), así que anular la
URL en el mismo proceso de pytest no es fiable — un subproceso limpio sí lo es.
"""

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

from core.config import get_settings

TEST_DB_NAME = "stratos_test"
CORE_ENGINE_DIR = Path(__file__).resolve().parent.parent


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
    """Conexion del rol owner dentro de una transaccion que siempre se
    deshace al final del test (SAVEPOINT pattern)."""
    engine = create_async_engine(test_database["owner_url"])
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            yield conn
        finally:
            await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    async with session:
        yield session


@pytest_asyncio.fixture
async def app_engine(test_database: dict[str, str]) -> AsyncIterator[object]:
    """Engine conectado como `stratos_app` (rol restringido) contra
    `stratos_test`, para los tests de inmutabilidad por permisos."""
    engine = create_async_engine(test_database["app_url"])
    yield engine
    await engine.dispose()
