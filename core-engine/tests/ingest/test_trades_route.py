"""PARTE 9.1: `POST /ingest/trades` end-to-end (ASGI real contra
`stratos_test`) -- idempotencia (P9), huerfanos (bot_id NULL no rechaza),
mismatch de sello (422, cero filas)."""

from typing import Any

from httpx import AsyncClient
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.market import IngestBatch, Trade
from core.ingest.schemas import TradesIngestRequest
from tests.factories import AccountFactory, BotFactory
from tests.ingest.conftest import TEST_INGEST_API_KEY

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _sealed_trades_payload(
    account_login: str, connector_instance_id: str, trades: list[dict[str, Any]]
) -> dict[str, Any]:
    draft = {
        "account_login": account_login,
        "connector_instance_id": connector_instance_id,
        "trades": trades,
        "batch_sha256": "0" * 64,
    }
    parsed = TradesIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "trades", [canonical_record])
    return {**draft, "batch_sha256": seal}


def _trade(ticket: int, magic: int) -> dict[str, Any]:
    return {
        "ticket_mt5": ticket,
        "symbol": "EURUSD",
        "magic_number": magic,
        "type": "BUY",
        "volume": 0.1,
        "open_time": "2026-08-20T09:00:00Z",
        "close_time": "2026-08-20T10:00:00Z",
        "open_price": 1.085,
        "close_price": 1.086,
        "sl": 1.08,
        "tp": 1.09,
        "profit": 10.5,
        "commission": -0.5,
        "swap": 0.0,
    }


async def test_ingests_new_trade_with_matching_bot(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    bot = BotFactory(account_id=None, magic_number=118231)
    async with _session(db_connection) as session:
        session.add(account)
        await session.flush()
        bot.account_id = account.id
        session.add(bot)
        await session.commit()

    payload = _sealed_trades_payload(account.login, "conn-1", [_trade(3000001, 118231)])
    response = await ingest_client.post("/ingest/trades", json=payload, headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 1
    assert body["duplicated"] == 0

    async with _session(db_connection) as session2:
        trade = (
            await session2.execute(select(Trade).where(Trade.ticket_mt5 == 3000001))
        ).scalar_one()
        assert trade.bot_id == bot.id
        assert trade.account_id == account.id
        batch = await session2.get(IngestBatch, body["batch_id"])
        assert batch is not None
        assert batch.sha256 == payload["batch_sha256"]


async def test_orphan_trade_is_not_rejected(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    # magic 999999: ningun Bot registrado con ese magic -> huerfano
    payload = _sealed_trades_payload(account.login, "conn-1", [_trade(3000002, 999999)])
    response = await ingest_client.post("/ingest/trades", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1

    async with _session(db_connection) as session2:
        trade = (
            await session2.execute(select(Trade).where(Trade.ticket_mt5 == 3000002))
        ).scalar_one()
        assert trade.bot_id is None


async def test_resend_same_batch_does_not_duplicate(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_trades_payload(account.login, "conn-1", [_trade(3000003, 118231)])
    first = await ingest_client.post("/ingest/trades", json=payload, headers=HEADERS)
    assert first.json()["accepted"] == 1
    assert first.json()["duplicated"] == 0

    second = await ingest_client.post("/ingest/trades", json=payload, headers=HEADERS)
    assert second.json()["accepted"] == 0
    assert second.json()["duplicated"] == 1
    # ambos intentos sellan su propio IngestBatch (append-only real), pero
    # solo hay 1 fila Trade
    assert first.json()["batch_id"] != second.json()["batch_id"]

    async with _session(db_connection) as session2:
        rows = (await session2.execute(select(Trade).where(Trade.ticket_mt5 == 3000003))).scalars()
        assert len(list(rows)) == 1


async def test_tampered_seal_is_rejected_and_persists_nothing(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_trades_payload(account.login, "conn-1", [_trade(3000004, 118231)])
    seal = payload["batch_sha256"]
    payload["batch_sha256"] = ("0" if seal[0] != "0" else "1") + seal[1:]

    response = await ingest_client.post("/ingest/trades", json=payload, headers=HEADERS)
    assert response.status_code != 200

    async with _session(db_connection) as session2:
        result = await session2.execute(select(Trade).where(Trade.ticket_mt5 == 3000004))
        assert result.first() is None


async def test_unknown_account_login_is_404(ingest_client: AsyncClient) -> None:
    payload = _sealed_trades_payload("no-such-login", "conn-1", [_trade(3000005, 118231)])
    response = await ingest_client.post("/ingest/trades", json=payload, headers=HEADERS)
    assert response.status_code == 404
