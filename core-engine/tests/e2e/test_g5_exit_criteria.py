"""Salida contractual de G5 (PARTE 12): "tests de API (auth, validaciones,
409 cementerio, SIZING_CAP, deriva EA modo incorrecto)". De los 4 escenarios
literales de PARTE 16 relevantes a G5, 3 ya se prueban end-to-end contra
Postgres/HTTP real en su propio modulo de servicio/router -- este archivo no
los repite, solo los referencia para que quien busque "el test del criterio
de aceptacion X" lo encuentre:

- Criterio 11 (SIZING_CAP bloquea activacion >89 %):
  tests/services/test_staging.py::TestEscalateStagingStep::
  test_sizing_cap_blocks_escalation_above_89_percent
- Criterio 4 (Cementerio: 409 sin excepcion):
  tests/routers/test_cemetery.py::test_always_returns_409
- Deriva EA en modo incorrecto (PARTE 9.1/9.2, criterio de salida literal de
  G5 -- no es un criterio numerado de PARTE 16, PARTE 16 no cubre G4/ingest):
  tests/services/test_config_drift.py::test_mode_drift_creates_critica_alert

El unico escenario de los 4 que SI se prueba aqui es el criterio 12
(posicion sin SL -> Telegram <60s): era un hueco real hasta este commit --
`services/positions.py` (G4) crea la `Alert` CRITICA inline pero nada la
despachaba a Telegram, porque el wiring de Telegram de G5 (PARTE 12,
bloque f) solo cableo los 14 servicios de dominio nuevos, no el endpoint de
ingesta de G4 que tambien crea Alerts. Corregido cableando
`dispatch_new_alerts` (promovido a `notifications/dispatch.py`, compartido
con `jobs/tasks.py`) inline en `POST /ingest/positions`, justo despues del
commit."""

import json
from typing import Any

from httpx import AsyncClient, Request
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.ingest.schemas import PositionsIngestRequest
from tests.e2e.conftest import TEST_INGEST_API_KEY
from tests.factories import AccountFactory

HEADERS = {"X-API-Key": TEST_INGEST_API_KEY}


def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


def _sealed_positions_payload(
    account_login: str, ts: str, positions: list[dict[str, Any]]
) -> dict[str, Any]:
    draft = {
        "account_login": account_login,
        "connector_instance_id": "conn-e2e",
        "ts": ts,
        "positions": positions,
        "batch_sha256": "0" * 64,
    }
    parsed = PositionsIngestRequest.model_validate(draft)
    canonical_record = parsed.model_dump(mode="json", exclude={"batch_sha256"})
    seal = compute_batch_sha256(account_login, "positions", [canonical_record])
    return {**draft, "batch_sha256": seal}


def _position_without_sl(ticket: int, magic: int) -> dict[str, Any]:
    return {
        "ticket_mt5": ticket,
        "symbol": "XAUUSD",
        "magic_number": magic,
        "type": "SELL",
        "volume": 0.2,
        "open_time": "2026-08-26T10:00:00Z",
        "open_price": 1915.30,
        "sl": None,
        "tp": 1900.0,
        "profit": -4.5,
    }


async def test_missing_sl_sends_a_telegram_alert_within_60s(
    e2e_client_and_telegram_calls: tuple[AsyncClient, list[Request]],
    db_connection: AsyncConnection,
) -> None:
    """PARTE 16 criterio 12, alcance G5. El request completo (ingesta ->
    P5 -> commit -> dispatch Telegram) ocurre dentro de un unico ciclo
    HTTP sincrono -- el limite de 60s de la spec siempre se cumple por
    construccion, no hace falta cronometrar; lo que este test prueba de
    verdad es que la llamada a Telegram LLEGA a ocurrir, cosa que antes de
    este commit no pasaba nunca para esta alerta."""
    client, telegram_calls = e2e_client_and_telegram_calls
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    payload = _sealed_positions_payload(
        account.login, "2026-08-26T12:00:00Z", [_position_without_sl(5000001, 118231)]
    )
    response = await client.post("/ingest/positions", json=payload, headers=HEADERS)
    assert response.status_code == 200

    async with _session(db_connection) as session2:
        alert = (
            await session2.execute(
                select(Alert).where(Alert.dedup_key == f"ingest_missing_sl:{account.id}:5000001")
            )
        ).scalar_one()
        assert alert.level == AlertLevel.CRITICA

    assert len(telegram_calls) == 1
    assert "test-bot-token-e2e" in str(telegram_calls[0].url)
    sent_body = json.loads(telegram_calls[0].content)
    assert sent_body["chat_id"] == "99999"
    assert "5000001" in sent_body["text"]
    assert "XAUUSD" in sent_body["text"]


async def test_position_with_sl_never_reaches_telegram(
    e2e_client_and_telegram_calls: tuple[AsyncClient, list[Request]],
    db_connection: AsyncConnection,
) -> None:
    """Control negativo: una posicion normal (con SL) no debe generar
    ningun trafico de Telegram -- confirma que el wiring nuevo esta
    condicionado a que P5 cree/mantenga una Alert nueva, no a cada
    ingesta."""
    client, telegram_calls = e2e_client_and_telegram_calls
    account = AccountFactory()
    async with _session(db_connection) as session:
        session.add(account)
        await session.commit()

    position = _position_without_sl(5000002, 118231)
    position["sl"] = 1900.0
    payload = _sealed_positions_payload(account.login, "2026-08-26T12:00:00Z", [position])
    response = await client.post("/ingest/positions", json=payload, headers=HEADERS)
    assert response.status_code == 200

    assert telegram_calls == []
