"""PARTE 6/9.1: sella y registra un `IngestBatch` -- comun a los 7
servicios de `services/`. `records` es SIEMPRE la lista de un solo dict con
el payload completo (menos `batch_sha256`, ya excluido por el caller): mas
simple y mas seguro que sellar solo la lista de items "de negocio" (trades/
positions/...) -- cubre tambien los campos escalares hermanos (`magic`,
`connector_instance_id`) que de lo contrario podrian alterarse sin invalidar
el sello."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from ingest_seal.sealing import verify_batch_seal
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AlertLevel
from core.db.models.accounts import Account
from core.db.models.decisions import Alert
from core.db.models.market import IngestBatch

# G13-75 (2026-09-28): un sello reenviado "unas pocas veces" (el escenario
# de diseno de esta funcion, "141 reenvios en 20 minutos") es ruido
# tolerable -- pero sin ninguna senal visible, un conector desactualizado
# que se queda reenviando el MISMO sello sin parar (causa raiz confirmada:
# version del conector sin el watermark incremental de poll_deals_
# incremental_once, ver docs/backlog.md G13-75) puede acumular decenas de
# miles de filas append-only durante semanas antes de que alguien lo note
# -- confirmado contra la cuenta real BEPB: 52.512 filas para un solo
# sello, 21 dias, sin ninguna alerta. El umbral es deliberadamente bajo
# (mucho antes de que el volumen sea un problema de rendimiento) porque el
# coste de una alerta de mas es minimo comparado con 3 semanas de silencio.
_EXCESSIVE_RESEND_ALERT_THRESHOLD = 50


def _excessive_resend_dedup_key(account_id: int, batch_type: str, sha256: str) -> str:
    return f"ingest_excessive_resend:{account_id}:{batch_type}:{sha256[:12]}"


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

    # `.limit(1)` es obligatorio: por diseno de esta misma funcion, un sello
    # reenviado dentro deja SU PROPIA fila cada vez (parrafo de arriba) -- el
    # conector reenviando el mismo lote una tercera vez dentro deja 2+ filas
    # con este mismo (account_id, batch_type, sha256), y sin el limite
    # `.scalar_one_or_none()` revienta con `MultipleResultsFound` en vez de
    # devolver `ya_visto=True`. Bug real en produccion, 2026-09-28: la
    # version anterior de este query tumbaba /ingest/equity y
    # /ingest/positions con 500 en cuanto un reenvio legitimo alcanzaba la
    # segunda repeticion del mismo sello -- exactamente el escenario "141
    # reenvios en 20 minutos" que motivo esta funcion.
    seal_filter = (
        IngestBatch.account_id == account.id,
        IngestBatch.batch_type == batch_type,
        IngestBatch.sha256 == claimed_sha256,
    )
    ya_registrado = (
        await session.execute(select(IngestBatch).where(*seal_filter).limit(1))
    ).scalar_one_or_none()
    if ya_registrado is not None:
        await _alert_if_excessive_resend(
            session, account.id, batch_type, claimed_sha256, seal_filter
        )
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


async def _alert_if_excessive_resend(
    session: AsyncSession,
    account_id: int,
    batch_type: str,
    claimed_sha256: str,
    seal_filter: Sequence[ColumnElement[bool]],
) -> None:
    """Genera una `Alert` (una sola vez por sello, via `dedup_key`) si un
    reenvio ya deja de ser el "141 en 20 minutos" tolerado por diseno y pasa
    a ser un conector atascado reenviando lo mismo sin parar. No revienta el
    ingest si falla la propia alerta -- llegar tarde a avisar es mejor que
    tumbar la ingesta real por un problema de observabilidad."""
    dedup_key = _excessive_resend_dedup_key(account_id, batch_type, claimed_sha256)
    ya_alertado = (
        await session.execute(
            select(Alert.id).where(Alert.dedup_key == dedup_key, Alert.resolved.is_(False))
        )
    ).scalar_one_or_none()
    if ya_alertado is not None:
        return

    n = (
        await session.execute(select(func.count()).select_from(IngestBatch).where(*seal_filter))
    ).scalar_one()
    if n < _EXCESSIVE_RESEND_ALERT_THRESHOLD:
        return

    session.add(
        Alert(
            ts=datetime.now(UTC),
            level=AlertLevel.SUAVE,
            module="ingest_batch",
            message=(
                f"Sello reenviado {n} veces sin ingerir nada nuevo (cuenta {account_id}, "
                f"{batch_type}). Probable conector desactualizado sin watermark incremental "
                "(ver docs/backlog.md G13-75) -- revisar la version desplegada."
            ),
            action_required="Confirmar y redesplegar la version actual del conector en esa cuenta.",
            dedup_key=dedup_key,
        )
    )
