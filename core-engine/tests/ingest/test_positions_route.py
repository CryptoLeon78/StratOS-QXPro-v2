"""PARTE 9.1: `POST /ingest/positions` end-to-end -- upsert guardado sobre
Trade (nunca resucita un trade cerrado), P5 (posicion sin SL -> Alert
CRITICA, auto-resuelta si el SL reaparece)."""

from typing import Any

from httpx import AsyncClient
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.db.models.market import Trade
from core.ingest.schemas import PositionsIngestRequest
from tests.factories import AccountFactory, BotFactory
from tests.ingest.conftest import TEST_INGEST_API_KEY

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _sealed_positions_payload(
    account_login: str,
    ts: str,
    positions: list[dict[str, Any]],
    connector_instance_id: str = "conn-1",
) -> dict[str, Any]:
    draft = {
        "account_login": account_login,
        "connector_instance_id": connector_instance_id,
        "ts": ts,
        "positions": positions,
        "batch_sha256": "0" * 64,
    }
    parsed = PositionsIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "positions", [canonical_record])
    return {**draft, "batch_sha256": seal}


def _position(ticket: int, magic: int, sl: float | None) -> dict[str, Any]:
    return {
        "ticket_mt5": ticket,
        "symbol": "EURUSD",
        "magic_number": magic,
        "type": "BUY",
        "volume": 0.1,
        "open_time": "2026-08-26T09:00:00Z",
        "open_price": 1.085,
        "sl": sl,
        "tp": 1.09,
        "profit": 3.2,
    }


async def test_new_open_position_is_inserted(
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

    payload = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position(4000001, 118231, 1.08)]
    )
    response = await ingest_client.post("/ingest/positions", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1

    async with _session(db_connection) as session2:
        trade = (
            await session2.execute(select(Trade).where(Trade.ticket_mt5 == 4000001))
        ).scalar_one()
        assert trade.bot_id == bot.id
        assert trade.close_time is None
        assert str(trade.sl) == "1.08000"


async def test_second_poll_updates_sl_tp_profit_of_same_open_position(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    first = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position(4000002, 118231, 1.08)]
    )
    await ingest_client.post("/ingest/positions", json=first, headers=HEADERS)

    moved = _position(4000002, 118231, 1.08)
    moved["sl"] = 1.084
    moved["profit"] = 9.9
    second = _sealed_positions_payload(account.login, "2026-08-26T12:00:05Z", [moved])
    response = await ingest_client.post("/ingest/positions", json=second, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1  # sigue abierta -> update cuenta como accepted

    async with _session(db_connection) as session2:
        rows = (
            (await session2.execute(select(Trade).where(Trade.ticket_mt5 == 4000002)))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert str(rows[0].sl) == "1.08400"
        assert str(rows[0].profit) == "9.90"


async def test_closed_trade_is_never_resurrected_by_a_late_position_update(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    opening = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position(4000003, 118231, 1.08)]
    )
    await ingest_client.post("/ingest/positions", json=opening, headers=HEADERS)

    async with _session(db_connection) as session:
        trade = (
            await session.execute(select(Trade).where(Trade.ticket_mt5 == 4000003))
        ).scalar_one()
        trade.close_time = trade.open_time
        trade.close_price = trade.open_price
        await session.commit()

    stale = _position(4000003, 118231, 1.08)
    stale["profit"] = -50.0
    late_update = _sealed_positions_payload(account.login, "2026-08-26T12:00:10Z", [stale])
    response = await ingest_client.post("/ingest/positions", json=late_update, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 0
    assert response.json()["duplicated"] == 1

    async with _session(db_connection) as session2:
        trade = (
            await session2.execute(select(Trade).where(Trade.ticket_mt5 == 4000003))
        ).scalar_one()
        assert trade.close_time is not None
        assert str(trade.profit) != "-50.00"


async def test_missing_sl_creates_critical_alert(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position(4000004, 118231, None)]
    )
    response = await ingest_client.post("/ingest/positions", json=payload, headers=HEADERS)
    assert response.status_code == 200

    async with _session(db_connection) as session2:
        alert = (
            await session2.execute(
                select(Alert).where(Alert.dedup_key == f"ingest_missing_sl:{account.id}:4000004")
            )
        ).scalar_one()
        assert alert.level == AlertLevel.CRITICA
        assert alert.resolved is False


async def test_missing_sl_alert_does_not_duplicate_on_repeated_polls(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    for ts in ("2026-08-26T12:00:00Z", "2026-08-26T12:00:05Z"):
        payload = _sealed_positions_payload(account.login, ts, [_position(4000005, 118231, None)])
        await ingest_client.post("/ingest/positions", json=payload, headers=HEADERS)

    async with _session(db_connection) as session2:
        rows = (
            (
                await session2.execute(
                    select(Alert).where(
                        Alert.dedup_key == f"ingest_missing_sl:{account.id}:4000005"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1


async def test_sl_reappearing_resolves_the_alert(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    missing = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position(4000006, 118231, None)]
    )
    await ingest_client.post("/ingest/positions", json=missing, headers=HEADERS)

    fixed = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:05Z", [_position(4000006, 118231, 1.08)]
    )
    await ingest_client.post("/ingest/positions", json=fixed, headers=HEADERS)

    async with _session(db_connection) as session2:
        alert = (
            await session2.execute(
                select(Alert).where(Alert.dedup_key == f"ingest_missing_sl:{account.id}:4000006")
            )
        ).scalar_one()
        assert alert.resolved is True
        assert alert.resolved_by == "system:ingest"


async def test_orphan_position_is_not_rejected(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position(4000007, 999999, 1.08)]
    )
    response = await ingest_client.post("/ingest/positions", json=payload, headers=HEADERS)
    assert response.status_code == 200

    async with _session(db_connection) as session2:
        trade = (
            await session2.execute(select(Trade).where(Trade.ticket_mt5 == 4000007))
        ).scalar_one()
        assert trade.bot_id is None


async def test_tampered_seal_is_rejected_and_persists_nothing(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position(4000008, 118231, 1.08)]
    )
    seal = payload["batch_sha256"]
    payload["batch_sha256"] = ("0" if seal[0] != "0" else "1") + seal[1:]

    response = await ingest_client.post("/ingest/positions", json=payload, headers=HEADERS)
    assert response.status_code == 422

    async with _session(db_connection) as session2:
        result = await session2.execute(select(Trade).where(Trade.ticket_mt5 == 4000008))
        assert result.first() is None


async def test_unknown_account_login_is_404(ingest_client: AsyncClient) -> None:
    payload = _sealed_positions_payload(
        "no-such-login", "2026-08-26T12:00:00Z", [_position(4000009, 118231, 1.08)]
    )
    response = await ingest_client.post("/ingest/positions", json=payload, headers=HEADERS)
    assert response.status_code == 404
