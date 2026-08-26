"""PARTE 7.9/14: checklists periodicas (dominical/quincenal/mensual/
trimestral/anual, "calendario de decisiones" literal del video). `sign_item`
acumula firmas item-a-item en `ChecklistItemSignature` (staging mutable,
aprobada por el operador, migracion G5-0004) y solo escribe la fila unica
e inmutable en `ChecklistRun` (ya migrada en G1) cuando el catalogo
completo del periodo queda firmado."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import ChecklistType
from core.db.models.governance import ChecklistItemSignature, ChecklistRun

# Refleja 1:1 `checklist_catalog` de config/thresholds.seed.json (literal
# del "calendario de decisiones" del video, doc_app/transcripcion_video_
# SIN__minutaje...md) -- el JSON es la fuente unica (P11).
DEFAULT_CHECKLIST_CATALOG: dict[ChecklistType, tuple[str, ...]] = {
    ChecklistType.SUNDAY: (
        "Revisar errores de EA",
        "Revisar desconexiones",
        "Revisar órdenes rechazadas",
        "Copiar las noticias de la semana entrante al filtro horario",
    ),
    ChecklistType.BIWEEKLY: (
        "Revisar semáforos contra línea base",
        "Confirmar que los bots en AMARILLO tienen el sizing al 50%",
    ),
    ChecklistType.MONTHLY: (
        "Comparar cada bot con su backtest y rebalancear los bloques "
        "si se desvían más de 10 puntos",
        "Revisar correlaciones",
        "Ejecutar el retiro mensual",
    ),
    ChecklistType.QUARTERLY: (
        "Revisión de robustez completa",
        "Chequeo de alfa/beta frente al benchmark",
        "Informe trimestral del coste de impulsos",
    ),
    ChecklistType.ANNUAL: ("Reestructuración anual del portfolio",),
}


@dataclass(frozen=True)
class ChecklistCatalog:
    items_by_type: dict[ChecklistType, tuple[str, ...]] = field(
        default_factory=lambda: DEFAULT_CHECKLIST_CATALOG
    )


def period_key_for(checklist_type: ChecklistType, now: datetime) -> str:
    if checklist_type == ChecklistType.SUNDAY:
        iso_year, iso_week, _ = now.isocalendar()
        return f"{iso_year:04d}-W{iso_week:02d}"
    if checklist_type == ChecklistType.BIWEEKLY:
        half = "H1" if now.day <= 15 else "H2"
        return f"{now.year:04d}-{now.month:02d}-{half}"
    if checklist_type == ChecklistType.MONTHLY:
        return f"{now.year:04d}-{now.month:02d}"
    if checklist_type == ChecklistType.QUARTERLY:
        quarter = (now.month - 1) // 3 + 1
        return f"{now.year:04d}-Q{quarter}"
    return f"{now.year:04d}"


async def get_progress(
    session: AsyncSession, checklist_type: ChecklistType, period_key: str
) -> list[ChecklistItemSignature]:
    rows = (
        await session.execute(
            select(ChecklistItemSignature).where(
                ChecklistItemSignature.checklist_type == checklist_type,
                ChecklistItemSignature.period_key == period_key,
            )
        )
    ).scalars()
    return list(rows.all())


async def sign_item(
    session: AsyncSession,
    checklist_type: ChecklistType,
    item_key: str,
    signed_by: str,
    catalog: ChecklistCatalog,
    now: datetime,
) -> ChecklistRun | None:
    catalog_items = catalog.items_by_type[checklist_type]
    if item_key not in catalog_items:
        raise ValueError(f"sign_item: '{item_key}' no esta en el catalogo de {checklist_type}")

    period_key = period_key_for(checklist_type, now)

    already_closed = (
        await session.execute(
            select(ChecklistRun.id).where(
                ChecklistRun.checklist_type == checklist_type,
                ChecklistRun.period_key == period_key,
            )
        )
    ).scalar_one_or_none()
    if already_closed is not None:
        raise ValueError("sign_item: este periodo ya tiene el checklist completado e inmutable")

    stmt = (
        pg_insert(ChecklistItemSignature)
        .values(
            checklist_type=checklist_type,
            period_key=period_key,
            item_key=item_key,
            signed_by=signed_by,
            signed_at=now,
        )
        .on_conflict_do_update(
            index_elements=["checklist_type", "period_key", "item_key"],
            set_={"signed_by": signed_by, "signed_at": now},
        )
    )
    await session.execute(stmt)
    await session.flush()

    signed_items = await get_progress(session, checklist_type, period_key)
    signed_keys = {row.item_key for row in signed_items}
    if signed_keys < set(catalog_items):
        return None

    items_payload = {row.item_key: row.signed_by for row in signed_items}
    canonical = json.dumps(items_payload, sort_keys=True, separators=(",", ":"))
    signature_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    run = ChecklistRun(
        ts=now,
        checklist_type=checklist_type,
        period_key=period_key,
        items=items_payload,
        completed=True,
        signed_by=signed_by,
        signature_hash=signature_hash,
    )
    session.add(run)
    await session.flush()
    return run
