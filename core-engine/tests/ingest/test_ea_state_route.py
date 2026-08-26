"""PARTE 9.1: `POST /ingest/ea_state` -- espejo del ultimo estado conocido
por EA (UPSERT real, PK account+magic)."""

from typing import Any

from httpx import AsyncClient
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.market import EaState
from core.ingest.schemas import EaStateIngestRequest
from tests.factories import AccountFactory
from tests.ingest.conftest import TEST_INGEST_API_KEY

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _ea(magic: int, ea_version: str, autotrading: bool) -> dict[str, Any]:
    return {
        "magic": magic,
        "ea_version": ea_version,
        "mode": "REAL",
        "autotrading": autotrading,
        "schedule_filter": {"days": ["MON", "TUE"]},
        "news_windows": [{"from": "12:00", "to": "13:00"}],
    }


def _sealed_ea_state_payload(account_login: str, eas: list[dict[str, Any]]) -> dict[str, Any]:
    draft = {
        "account_login": account_login,
        "connector_instance_id": "conn-1",
        "eas": eas,
        "batch_sha256": "0" * 64,
    }
    parsed = EaStateIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "ea_state", [canonical_record])
    return {**draft, "batch_sha256": seal}


async def test_ingests_ea_state(ingest_client: AsyncClient, db_connection: AsyncConnection) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_ea_state_payload(account.login, [_ea(118231, "1.0.0", True)])
    response = await ingest_client.post("/ingest/ea_state", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1

    async with _session(db_connection) as session2:
        state = await session2.get(EaState, (account.id, 118231))
        assert state is not None
        assert state.ea_version == "1.0.0"
        assert state.autotrading is True


async def test_second_report_upserts_the_same_row(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    first = _sealed_ea_state_payload(account.login, [_ea(118231, "1.0.0", True)])
    await ingest_client.post("/ingest/ea_state", json=first, headers=HEADERS)

    second = _sealed_ea_state_payload(account.login, [_ea(118231, "1.0.1", False)])
    response = await ingest_client.post("/ingest/ea_state", json=second, headers=HEADERS)
    assert response.status_code == 200

    async with _session(db_connection) as session2:
        state = await session2.get(EaState, (account.id, 118231))
        assert state is not None
        assert state.ea_version == "1.0.1"
        assert state.autotrading is False


async def test_tampered_seal_is_rejected(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_ea_state_payload(account.login, [_ea(118231, "1.0.0", True)])
    seal = payload["batch_sha256"]
    payload["batch_sha256"] = ("0" if seal[0] != "0" else "1") + seal[1:]

    response = await ingest_client.post("/ingest/ea_state", json=payload, headers=HEADERS)
    assert response.status_code == 422
