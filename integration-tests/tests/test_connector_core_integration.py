"""Criterio de salida de G4 (PARTE 12): "integracion conector<->core con
simulador; corte de 10 min sin perdidas ni duplicados". Unico test que usa
los 3 paquetes a la vez: `mt5-simulator` (datos), `mt5-connector`
(poller+buffer+sender, la logica real de store-and-forward), `core-engine`
(la app FastAPI real, contra `stratos_test` real -- Postgres real, no un
mock).

Compresion de tiempo, honesto: NO se ejecuta un corte real de 10 minutos
de reloj. `FlakyTransport` falla las primeras N peticiones (simulando el
corte) y `drain_once` se llama repetidamente en un bucle rapido (no via
`run_loop`, que usaria `asyncio.sleep` real) -- se prueba el MISMO
mecanismo (buffer que acumula durante el fallo, backoff, drenaje limpio al
recuperarse) a escala de segundos, no de minutos reales."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from connector.buffer import Buffer
from connector.http_client import BackoffConfig
from connector.poller import (
    poll_deals_incremental_once,
    poll_equity_once,
    poll_heartbeat_once,
    poll_positions_once,
)
from connector.sender import drain_once
from core.config import Settings, get_settings
from core.db.base import get_session
from core.db.enums import BotProfile, BotRole, PipelinePhase, SemaphoreState
from core.db.models.accounts import Account, Bot
from core.db.models.market import EquitySnapshot, HeartbeatLog, Trade
from core.main import app
from simulator.client import SimulatedMt5Client, TimelineStep
from simulator.scenarios.corte_de_red import FlakyTransport
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

ACCOUNT_LOGIN = "100231"
CONNECTOR_ID = "conn-integration-1"
INGEST_API_KEY = "integration-test-key"
MAGIC = 118231


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret="x",
        ingest_api_keys=INGEST_API_KEY,
    )


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _build_timeline() -> list[TimelineStep]:
    """Un unico trade (ticket 9000001) que el poller ve dos veces: abierto
    via `/ingest/positions` y, en el mismo poll, ya reportado como cerrado
    via `/ingest/trades` (mismo ticket+open_time) -- ejercita el upsert
    guardado de PARTE 9.1 (`positions` abre la fila, `trades` la cierra)
    dentro de un unico ciclo de outage/recovery. Debe quedar 1 sola fila
    Trade, no 2."""
    from connector.protocol import AccountInfoDTO, DealDTO, PositionDTO

    equity_early = Decimal("100000.00")
    equity_late = Decimal("100050.00")
    open_time = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    close_time = datetime(2026, 8, 26, 9, 30, tzinfo=UTC)
    return [
        TimelineStep(
            elapsed_seconds=0.0,
            account=AccountInfoDTO(
                balance=equity_early, equity=equity_early, margin_level=1500.0, margin_free=None
            ),
            positions=[
                PositionDTO(
                    ticket=9000001,
                    symbol="EURUSD",
                    type="BUY",
                    volume=Decimal("0.10"),
                    price_open=Decimal("1.08500"),
                    sl=Decimal("1.08000"),
                    tp=Decimal("1.09000"),
                    profit=Decimal("3.20"),
                    magic=MAGIC,
                    time=open_time,
                )
            ],
            new_deals=[
                DealDTO(
                    ticket=9000001,
                    symbol="EURUSD",
                    type="BUY",
                    volume=Decimal("0.10"),
                    price_open=Decimal("1.08500"),
                    price_close=Decimal("1.08700"),
                    sl=Decimal("1.08000"),
                    tp=Decimal("1.09000"),
                    profit=Decimal("5.00"),
                    commission=Decimal("-0.30"),
                    swap=Decimal("0.00"),
                    magic=MAGIC,
                    time_open=open_time,
                    time_close=close_time,
                )
            ],
        ),
        TimelineStep(
            elapsed_seconds=60.0,
            account=AccountInfoDTO(
                balance=equity_late, equity=equity_late, margin_level=1600.0, margin_free=None
            ),
        ),
    ]


async def test_outage_then_recovery_zero_loss_zero_duplicates(
    db_connection: AsyncConnection, tmp_path: Path
) -> None:
    # --- arrange: cuenta + bot en stratos_test real ---
    async with _session(db_connection) as session:
        account = Account(
            name="Integration Account",
            broker="Darwinex",
            login=ACCOUNT_LOGIN,
            server="Darwinex-Live",
            currency="EUR",
            is_demo=False,
            connector_instance_id=None,
            is_active=True,
        )
        session.add(account)
        await session.flush()
        bot = Bot(
            account_id=account.id,
            magic_number=MAGIC,
            name="Integration Bot",
            market="EURUSD",
            timeframe="H1",
            profile=BotProfile.TREND,
            role=BotRole.CHAMPION,
            slot=None,
            pipeline_phase=PipelinePhase.F7,
            semaphore_state=SemaphoreState.VERDE,
            entered_state_at=datetime.now(UTC),
            capital_allocated_pct=Decimal("4.00"),
            risk_per_trade_pct=Decimal("0.500"),
            sizing_multiplier=Decimal("1.00"),
            sizing_current_pct=Decimal("100.00"),
            kelly_fraction=Decimal("0.25"),
            created_at=datetime.now(UTC),
            baseline_id=None,
        )
        session.add(bot)
        await session.commit()

    # --- app real, DB real (stratos_test), settings controlados ---
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        async with session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_settings] = _settings

    real_transport = httpx.ASGITransport(app=app)
    # las 3 primeras peticiones fallan (corte de red simulado, comprimido
    # en el tiempo -- ver docstring del modulo)
    flaky_transport = FlakyTransport(wrapped=real_transport, fail_calls=3)

    buffer = Buffer(str(tmp_path / "outbox.sqlite"))
    await buffer.connect()
    client_mt5 = SimulatedMt5Client(_build_timeline())
    backoff = BackoffConfig(base_seconds=0.01, multiplier=1.0, max_seconds=0.01)

    try:
        async with httpx.AsyncClient(
            transport=flaky_transport, base_url="http://core.test"
        ) as http_client:
            # --- el poller encola durante el "corte" (nunca toca la red) ---
            await poll_positions_once(client_mt5, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)
            await poll_deals_incremental_once(client_mt5, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)
            await poll_equity_once(client_mt5, buffer, ACCOUNT_LOGIN, CONNECTOR_ID)
            await poll_heartbeat_once(buffer, ACCOUNT_LOGIN, CONNECTOR_ID, latency_ms=50)

            enqueued = await buffer.due_batches(datetime.now(UTC), limit=100)
            assert len(enqueued) == 4  # nada se perdio al encolar

            # --- drenaje: los primeros 3 intentos fallan (FlakyTransport),
            # drain_once no pierde filas (quedan en el buffer con backoff),
            # hasta que "se recupera la red" y drena todo. Se pasa un `now`
            # cada vez mas futuro (no un sleep real) para que las filas
            # reintentadas ya esten "vencidas" en la siguiente pasada --
            # compresion de tiempo deliberada, ver docstring del modulo. ---
            total_sent = 0
            probe_time = datetime.now(UTC)
            for i in range(8):  # suficientes ciclos para agotar los 3 fallos + drenar 4 lotes
                probe_time = datetime.now(UTC) + timedelta(seconds=i)
                total_sent += await drain_once(
                    http_client, buffer, INGEST_API_KEY, backoff, probe_time
                )

            assert total_sent == 4
            assert flaky_transport.attempts >= 4 + 3  # 3 fallos + al menos 4 exitos
            remaining = await buffer.due_batches(probe_time, limit=100)
            assert remaining == []  # buffer completamente vacio, cero perdidas
    finally:
        await buffer.close()
        app.dependency_overrides.clear()

    # --- assert final contra Postgres real: cero duplicados ---
    async with _session(db_connection) as verify_session:
        trade_count = (
            await verify_session.execute(select(func.count()).select_from(Trade))
        ).scalar_one()
        assert trade_count == 1  # el unico deal, ni perdido ni duplicado

        equity_count = (
            await verify_session.execute(select(func.count()).select_from(EquitySnapshot))
        ).scalar_one()
        assert equity_count == 1  # el unico snapshot encolado, ni perdido ni duplicado

        heartbeat_count = (
            await verify_session.execute(select(func.count()).select_from(HeartbeatLog))
        ).scalar_one()
        assert heartbeat_count == 1
