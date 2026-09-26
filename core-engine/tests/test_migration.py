"""PARTE 12 G1, criterio de salida: "migracion limpia". `test_database`
(session-scoped en conftest.py) ya aplico `alembic upgrade head` contra
`stratos_test` antes de que estos tests corran; aqui se verifica el
resultado real en el catalogo de Postgres/TimescaleDB."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

# PARTE 5.2 (25) + ea_state/virtual_trade (G4) + checklist_item_signature (G5)
# + instrument_spec/symbol_currency (G10, docs/backlog.md) + las 6 de G11/G13 de abajo.
EXPECTED_TABLE_COUNT = 39

# Tablas anadidas despues de G10. Se comprueban por nombre y no solo por recuento: un
# recuento suelto no dice cual falta ni cual sobra cuando una migracion se olvida.
EXPECTED_G11_G13_TABLES = {
    "import_artifact",  # G11, importacion administrativa trazable
    "execution_fill",  # G11, fills y rechazos del reporter v1.1
    "pipeline_phase_transition",  # G11, historico de pipeline
    "external_ea_inventory",  # G13, inventario de EAs externos observados
    "operational_asset",  # G13, catalogo de Analisis
    "operational_asset_event",  # G13, admision append-only
    "pipeline_work_item",  # G13-43, plano de control F0--F7
    "pipeline_agent_command",  # G13-46, solicitud idempotente al agente
    "pipeline_agent_command_event",  # G13-46, resultado terminal append-only
}


async def _table_names(db_connection: AsyncConnection) -> set[str]:
    result = await db_connection.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
    )
    names = {row[0] for row in result}
    names.discard("alembic_version")
    return names


async def test_all_tables_created(db_connection: AsyncConnection) -> None:
    names = await _table_names(db_connection)
    assert len(names) == EXPECTED_TABLE_COUNT, (
        f"se esperaban {EXPECTED_TABLE_COUNT} tablas y hay {len(names)}. "
        "Si una migracion nueva anade o quita una tabla, actualiza tambien esta constante."
    )


async def test_g11_g13_tables_created(db_connection: AsyncConnection) -> None:
    """Las 6 tablas posteriores a G10 existen con su nombre exacto."""
    names = await _table_names(db_connection)
    assert EXPECTED_G11_G13_TABLES <= names, (
        f"faltan tablas de G11/G13: {sorted(EXPECTED_G11_G13_TABLES - names)}"
    )


async def test_hypertables_created(db_connection: AsyncConnection) -> None:
    result = await db_connection.execute(
        text("SELECT hypertable_name FROM timescaledb_information.hypertables")
    )
    names = {row[0] for row in result}
    assert names == {"trade", "equity_snapshot", "heartbeat_log"}


async def test_equity_daily_continuous_aggregate_created(db_connection: AsyncConnection) -> None:
    result = await db_connection.execute(
        text("SELECT view_name, hypertable_name FROM timescaledb_information.continuous_aggregates")
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
