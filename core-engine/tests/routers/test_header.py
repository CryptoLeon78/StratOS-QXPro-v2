from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import AccountDataOrigin
from core.db.models.market import HeartbeatLog
from core.main import app
from tests.factories import (
    AccountFactory,
    BotFactory,
    EquitySnapshotFactory,
    IngestBatchFactory,
    TradeFactory,
)


async def test_header_summary_requires_auth() -> None:
    # sin dependency_overrides: get_current_user real, sin token -> 401.
    # El flujo completo de auth ya esta probado en tests/auth/.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/header/summary")
    assert response.status_code == 401


async def test_header_summary_reflects_real_equity_and_open_positions(
    api_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory(is_demo=False)
    session.add(account)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        EquitySnapshotFactory(
            account_id=account.id, ts=now - timedelta(days=10), equity=Decimal("100000")
        )
    )
    session.add(EquitySnapshotFactory(account_id=account.id, ts=now, equity=Decimal("105000")))
    await session.commit()

    response = await api_client.get("/api/v1/header/summary")
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["equity_eur"]) == Decimal("105000")
    assert body["open_positions"] == 0
    assert body["mt_connected"] is False


async def test_header_summary_hides_fresh_heartbeat_age(
    api_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory(is_demo=False)
    session.add(account)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        HeartbeatLog(
            ts=now - timedelta(seconds=1),
            connector_instance_id="test-connector",
            account_id=account.id,
            latency_ms=0,
            status="OK",
        )
    )
    await session.commit()

    response = await api_client.get("/api/v1/header/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["mt_connected"] is True
    assert body["data_stale_seconds"] is None


async def test_header_summary_reports_age_after_heartbeat_threshold(
    api_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory(is_demo=False)
    session.add(account)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        HeartbeatLog(
            ts=now - timedelta(seconds=121),
            connector_instance_id="test-connector",
            account_id=account.id,
            latency_ms=0,
            status="OK",
        )
    )
    await session.commit()

    response = await api_client.get("/api/v1/header/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["mt_connected"] is False
    assert body["data_stale_seconds"] is not None
    assert body["data_stale_seconds"] >= 120


async def test_equity_curve_returns_points_for_range(
    api_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory(is_demo=False)
    session.add(account)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        EquitySnapshotFactory(
            account_id=account.id, ts=now - timedelta(days=5), equity=Decimal("50000")
        )
    )
    await session.commit()

    response = await api_client.get("/api/v1/summary/equity-curve", params={"range": "30d"})
    assert response.status_code == 200
    assert len(response.json()) >= 1


class TestDataProvenance:
    """De qué universos se compone lo que muestran las vistas agregadas.

    En Portfolio, Salud, Riesgo, Auditoría y Dominical la procedencia no es un campo de una
    fila: es una propiedad del agregado. El recorrido G12 encontró que esas superficies
    sumaban fixture y telemetría real sin que nada lo dijera. Este endpoint declara la
    composición real de los datos, para que la UI pueda decirlo en vez de callarlo.
    """

    async def test_reports_a_single_origin_when_everything_comes_from_one(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        account = AccountFactory(data_origin=AccountDataOrigin.BROKER_REAL)
        session.add(account)
        await session.flush()
        session.add(BotFactory(account_id=account.id))
        await session.commit()

        response = await api_client.get("/api/v1/data-provenance")

        assert response.status_code == 200
        body = response.json()
        assert body["is_mixed"] is False
        assert [row["data_origin"] for row in body["accounts"]] == ["BROKER_REAL"]
        assert body["accounts"][0]["accounts"] == 1
        assert body["accounts"][0]["bots"] == 1

    async def test_flags_a_mixed_surface(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        """Fixture y telemetría real en la misma cifra: el hallazgo abierto de G12."""
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        real = AccountFactory(data_origin=AccountDataOrigin.BROKER_REAL)
        fixture = AccountFactory(data_origin=AccountDataOrigin.FIXTURE)
        session.add_all([real, fixture])
        await session.commit()

        response = await api_client.get("/api/v1/data-provenance")

        body = response.json()
        assert body["is_mixed"] is True
        assert set(row["data_origin"] for row in body["accounts"]) == {"BROKER_REAL", "FIXTURE"}

    async def test_an_empty_base_is_absence_not_a_guess(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        response = await api_client.get("/api/v1/data-provenance")

        body = response.json()
        assert body["accounts"] == []
        assert body["is_mixed"] is False


class TestTradeAttributionCoverage:
    """Que parte de las cifras agregadas pertenece a un bot vivo (backlog A17).

    Las metricas POR BOT ya cubren solo EAs vivos: un EA retirado no tiene fila en `bot`, asi
    que no aparece. El hueco esta en los agregados de Portfolio, Riesgo y Auditoria, que suman
    todos los trades de la cuenta -- incluidos los de EAs que se retiraron hace meses y los
    del historico HTML sin magic. Decision del operador: no se inventarian los retirados, pero
    la cifra tiene que decir cuanta de ella no es de ningun bot vivo.
    """

    async def test_reports_how_much_of_the_aggregate_belongs_to_a_live_bot(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        account = AccountFactory(data_origin=AccountDataOrigin.BROKER_REAL)
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        # Uno atribuido, uno de un EA retirado (magic desconocido) y uno sin EA (magic 0).
        session.add(
            TradeFactory(
                account_id=account.id,
                bot_id=bot.id,
                magic_number=bot.magic_number,
                ingest_batch_id=batch.id,
            )
        )
        session.add(
            TradeFactory(
                account_id=account.id,
                bot_id=None,
                magic_number=999999,
                ingest_batch_id=batch.id,
            )
        )
        session.add(
            TradeFactory(
                account_id=account.id, bot_id=None, magic_number=0, ingest_batch_id=batch.id
            )
        )
        await session.commit()

        body = (await api_client.get("/api/v1/data-provenance")).json()

        cobertura = body["trade_attribution"]
        assert cobertura["total"] == 3
        assert cobertura["attributed_to_live_bot"] == 1
        assert cobertura["retired_ea"] == 1
        assert cobertura["without_ea"] == 1
        assert cobertura["coverage_pct"] == 33.33

    async def test_no_trades_is_absence_not_zero_coverage(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        body = (await api_client.get("/api/v1/data-provenance")).json()

        assert body["trade_attribution"]["total"] == 0
        assert body["trade_attribution"]["coverage_pct"] is None
