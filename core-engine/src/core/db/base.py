from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(
    database_url: str,
    *,
    pool_size: int | None = None,
    max_overflow: int | None = None,
) -> AsyncEngine:
    """El tamano del pool se declara; no se hereda del default de la libreria.

    El stack operacional recibe telemetria de varias cuentas mientras el
    operador usa la UI. Con 5 + 10 conexiones la ingesta las agota y el login
    se queda esperando 30 s hasta devolver 500, sin que nada diga por que.
    """
    settings = get_settings()
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size if pool_size is None else pool_size,
        max_overflow=settings.db_max_overflow if max_overflow is None else max_overflow,
    )


engine = make_engine(get_settings().app_database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
