"""PARTE 9.1: `POST /ingest/execution` -- v1.1 EA reporter, "sin consumidor
aun" (literal): solo sella el lote, no persiste `fills`."""

from typing import Any

from httpx import AsyncClient
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.market import IngestBatch
from core.ingest.schemas import ExecutionIngestRequest
from tests.factories import AccountFactory
from tests.ingest.conftest import TEST_INGEST_API_KEY

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _fill(order_id: str) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "symbol": "EURUSD",
        "requested_price": 1.0850,
        "executed_price": 1.0851,
        "spread": 0.0001,
        "ts": "2026-08-26T12:00:00Z",
    }


def _sealed_execution_payload(
    account_login: str, magic: int, fills: list[dict[str, Any]]
) -> dict[str, Any]:
    draft = {
        "account_login": account_login,
        "connector_instance_id": "conn-1",
        "magic": magic,
        "fills": fills,
        "batch_sha256": "0" * 64,
    }
    parsed = ExecutionIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "execution", [canonical_record])
    return {**draft, "batch_sha256": seal}


async def test_seals_batch_without_persisting_fills(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_execution_payload(account.login, 118231, [_fill("ord-1"), _fill("ord-2")])
    response = await ingest_client.post("/ingest/execution", json=payload, headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 2
    assert body["duplicated"] == 0

    async with _session(db_connection) as session2:
        batch = await session2.get(IngestBatch, body["batch_id"])
        assert batch is not None
        assert batch.batch_type == "execution"
        assert batch.records == 2


async def test_tampered_seal_is_rejected(
    ingest_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_execution_payload(account.login, 118231, [_fill("ord-3")])
    seal = payload["batch_sha256"]
    payload["batch_sha256"] = ("0" if seal[0] != "0" else "1") + seal[1:]

    response = await ingest_client.post("/ingest/execution", json=payload, headers=HEADERS)
    assert response.status_code == 422
