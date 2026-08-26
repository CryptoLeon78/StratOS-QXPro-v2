"""PARTE 9.1: `POST /ingest/signals` -- trades virtuales (NARANJA), persisten
en VirtualTrade, no en Trade."""

from typing import Any

from httpx import AsyncClient
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.market import VirtualTrade
from core.ingest.schemas import SignalsIngestRequest
from tests.factories import AccountFactory, BotFactory
from tests.ingest.conftest import TEST_INGEST_API_KEY

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _signal(signal_id: str) -> dict[str, Any]:
    return {
        "signal_id": signal_id,
        "symbol": "XAUUSD",
        "type": "SELL",
        "volume": 0.1,
        "entry_price": 2400.0,
        "sl": 2410.0,
        "tp": 2380.0,
        "ts": "2026-08-26T12:00:00Z",
    }


def _sealed_signals_payload(
    account_login: str, magic: int, signals: list[dict[str, Any]]
) -> dict[str, Any]:
    draft = {
        "account_login": account_login,
        "connector_instance_id": "conn-1",
        "magic": magic,
        "signals": signals,
        "batch_sha256": "0" * 64,
    }
    parsed = SignalsIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "signals", [canonical_record])
    return {**draft, "batch_sha256": seal}


async def test_ingests_signal_with_matching_bot(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    bot = BotFactory(account_id=None, magic_number=118344)
    async with _session(db_connection) as session:
        session.add(account)
        await session.flush()
        bot.account_id = account.id
        session.add(bot)
        await session.commit()

    payload = _sealed_signals_payload(account.login, 118344, [_signal("sig-1")])
    response = await ingest_client.post("/ingest/signals", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1

    async with _session(db_connection) as session2:
        vt = (
            await session2.execute(select(VirtualTrade).where(VirtualTrade.signal_id == "sig-1"))
        ).scalar_one()
        assert vt.bot_id == bot.id
        assert vt.magic_number == 118344


async def test_resend_same_signal_does_not_duplicate(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_signals_payload(account.login, 118344, [_signal("sig-2")])
    first = await ingest_client.post("/ingest/signals", json=payload, headers=HEADERS)
    assert first.json()["accepted"] == 1

    second = await ingest_client.post("/ingest/signals", json=payload, headers=HEADERS)
    assert second.json()["accepted"] == 0
    assert second.json()["duplicated"] == 1


async def test_unknown_account_login_is_404(ingest_client: AsyncClient) -> None:
    payload = _sealed_signals_payload("no-such-login", 118344, [_signal("sig-3")])
    response = await ingest_client.post("/ingest/signals", json=payload, headers=HEADERS)
    assert response.status_code == 404
