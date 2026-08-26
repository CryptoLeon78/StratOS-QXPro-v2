"""PARTE 9.1: `POST /ingest/heartbeat`. `ts` la pone el cliente (no en la
notacion compacta de PARTE 9.1, pero HeartbeatLog.ts es parte de su PK --
ver ASSUMPTIONS G4-11) para que un reenvio real dedupe."""

from typing import Any

from httpx import AsyncClient
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.market import HeartbeatLog
from core.ingest.schemas import HeartbeatIngestRequest
from tests.factories import AccountFactory
from tests.ingest.conftest import TEST_INGEST_API_KEY

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _sealed_heartbeat_payload(
    account_login: str, connector_instance_id: str, ts: str, latency_ms: int
) -> dict[str, Any]:
    draft = {
        "connector_instance_id": connector_instance_id,
        "account_login": account_login,
        "latency_ms": latency_ms,
        "ts": ts,
        "batch_sha256": "0" * 64,
    }
    parsed = HeartbeatIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "heartbeat", [canonical_record])
    return {**draft, "batch_sha256": seal}


async def test_ingests_heartbeat(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_heartbeat_payload(account.login, "conn-1", "2026-08-26T12:00:00Z", 42)
    response = await ingest_client.post("/ingest/heartbeat", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1

    async with _session(db_connection) as session2:
        log = (
            await session2.execute(
                select(HeartbeatLog).where(HeartbeatLog.account_id == account.id)
            )
        ).scalar_one()
        assert log.latency_ms == 42
        assert log.status == "OK"


async def test_resend_same_heartbeat_does_not_duplicate(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_heartbeat_payload(account.login, "conn-1", "2026-08-26T12:00:00Z", 42)
    first = await ingest_client.post("/ingest/heartbeat", json=payload, headers=HEADERS)
    assert first.json()["accepted"] == 1

    second = await ingest_client.post("/ingest/heartbeat", json=payload, headers=HEADERS)
    assert second.json()["accepted"] == 0
    assert second.json()["duplicated"] == 1


async def test_tampered_seal_is_rejected(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_heartbeat_payload(account.login, "conn-1", "2026-08-26T12:00:00Z", 42)
    seal = payload["batch_sha256"]
    payload["batch_sha256"] = ("0" if seal[0] != "0" else "1") + seal[1:]

    response = await ingest_client.post("/ingest/heartbeat", json=payload, headers=HEADERS)
    assert response.status_code == 422
