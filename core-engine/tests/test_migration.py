"""PARTE 12 G1, criterio de salida: "migracion limpia". `test_database`
(session-scoped en conftest.py) ya aplico `alembic upgrade head` contra
`stratos_test` antes de que estos tests corran; aqui se verifica el
resultado real en el catalogo de Postgres/TimescaleDB."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

EXPECTED_TABLE_COUNT = 25  # PARTE 5.2


async def test_all_tables_created(db_connection: AsyncConnection) -> None:
    result = await db_connection.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
    )
    names = {row[0] for row in result}
    names.discard("alembic_version")
    assert len(names) == EXPECTED_TABLE_COUNT


async def test_hypertables_created(db_connection: AsyncConnection) -> None:
    result = await db_connection.execute(
        text("SELECT hypertable_name FROM timescaledb_information.hypertables")
    )
    names = {row[0] for row in result}
    assert names == {"trade", "equity_snapshot", "heartbeat_log"}


async def test_equity_daily_continuous_aggregate_created(db_connection: AsyncConnection) -> None:
    result = await db_connection.execute(
        text(
            "SELECT view_name, hypertable_name FROM timescaledb_information.continuous_aggregates"
        )
    )
    rows = {(row[0], row[1]) for row in result}
    assert ("equity_daily", "equity_snapshot") in rows


async def test_compression_and_retention_policies_registered(
    db_connection: AsyncConnection,
) -> None:
    result = await db_connection.execute(
        text(
            "SELECT hypertable_name, proc_name FROM timescaledb_information.jobs "
            "WHERE proc_name IN ('policy_compression', 'policy_retention')"
        )
    )
    rows = {(row[0], row[1]) for row in result}
    assert ("trade", "policy_compression") in rows
    assert ("equity_snapshot", "policy_compression") in rows
    assert ("heartbeat_log", "policy_retention") in rows


async def test_stratos_app_role_exists(db_connection: AsyncConnection) -> None:
    result = await db_connection.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = 'stratos_app'")
    )
    assert result.scalar() == 1
