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
from sqlalchemy import select
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
) -> tuple[IngestBatch, bool]:
    """Verifica el sello (fail-closed: `SealMismatchError` sin tocar la
    sesion si no coincide) y crea la fila `IngestBatch`. El caller decide
    `record_count` (cuantos "items de negocio" logicos hay en el lote --
    puede diferir de `len(records)`, que aqui siempre es 1).

    Devuelve `(lote, ya_visto)`. El lote **siempre** se sella y se registra,
    tambien cuando se repite: cada intento deja su propia fila, que es lo que
    hace de `IngestBatch` un registro append-only real y lo que permite ver
    que un conector esta reenviando (el 2026-09-26, 141 reenvios del historico
    completo en 20 minutos).

    `ya_visto` avisa de que ese sello -- que cubre
    `(account_login, batch_type, records)` -- ya estaba registrado para la
    cuenta, asi que el lote es byte a byte el mismo y **no hay nada que
    ingerir**. El caller salta el reproceso y responde `accepted=0`.

    Evitarlo no es una optimizacion, es defensa propia: repetir miles de
    upserts que colisionan entre si serializa la ingesta y tumba al resto del
    sistema. Lo que se evita es el trabajo, nunca la traza.
    """
    verify_batch_seal(claimed_sha256, account_login, batch_type, records)

    ya_registrado = (
        await session.execute(
            select(IngestBatch).where(
                IngestBatch.account_id == account.id,
                IngestBatch.batch_type == batch_type,
                IngestBatch.sha256 == claimed_sha256,
            )
        )
    ).scalar_one_or_none()
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
    return batch, ya_registrado is not None
