"""PARTE 6/9.1: sella y registra un `IngestBatch` -- comun a los 7
servicios de `services/`. `records` es SIEMPRE la lista de un solo dict con
el payload completo (menos `batch_sha256`, ya excluido por el caller): mas
simple y mas seguro que sellar solo la lista de items "de negocio" (trades/
positions/...) -- cubre tambien los campos escalares hermanos (`magic`,
`connector_instance_id`) que de lo contrario podrian alterarse sin invalidar
el sello."""

from datetime import UTC, datetime
from typing import Any

from ingest_seal.sealing import verify_batch_seal
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account
from core.db.models.market import IngestBatch


async def seal_and_create_batch(
    session: AsyncSession,
    account: Account,
    batch_type: str,
    account_login: str,
    connector_instance_id: str,
    claimed_sha256: str,
    records: list[dict[str, Any]],
    record_count: int,
) -> IngestBatch:
    """Verifica el sello (fail-closed: `SealMismatchError` sin tocar la
    sesion si no coincide) y crea la fila `IngestBatch`. El caller decide
    `record_count` (cuantos "items de negocio" logicos hay en el lote --
    puede diferir de `len(records)`, que aqui siempre es 1)."""
    verify_batch_seal(claimed_sha256, account_login, batch_type, records)

    now = datetime.now(UTC)
    batch = IngestBatch(
        ts=now,
        connector_instance_id=connector_instance_id,
        account_id=account.id,
        batch_type=batch_type,
        records=record_count,
        sha256=claimed_sha256,
        server_ts=now,
    )
    session.add(batch)
    await session.flush()
    return batch
