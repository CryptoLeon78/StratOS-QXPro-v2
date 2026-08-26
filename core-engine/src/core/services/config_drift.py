"""PARTE 7.2 ("Panel Deriva de configuracion", diseño derivado sin captura)
+ criterio de salida literal de G5 ("deriva EA modo incorrecto"). Compara
el modo esperado (derivado de `Bot.semaphore_state`: NARANJA -> PAPER,
cualquier otro -> REAL) contra `EaState.mode` (G4, ultimo estado reportado).

Hueco real de esquema (documentar, no corregir aqui): el payload de
`POST /ingest/ea_state` (PARTE 9.1) no reporta el sizing aplicado por el
EA, solo `mode`/`autotrading`/`schedule_filter`/`news_windows` -- el "sizing
aplicado vs sizing_current_pct" que describe 7.2 no es computable con el
contrato de ingesta actual. Este modulo solo cubre deriva de MODO."""

import json
from dataclasses import dataclass
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AlertLevel, SemaphoreState
from core.db.models.accounts import Bot
from core.db.models.decisions import Alert
from core.db.models.market import EaState

_PAPER = "PAPER"
_REAL = "REAL"


@dataclass(frozen=True)
class ConfigDriftRow:
    bot_id: int
    account_id: int
    magic_number: int
    expected_mode: str
    reported_mode: str
    drift: bool


@dataclass(frozen=True)
class OrphanReport:
    orphan_magics: list[tuple[int, int]]
    missing_magics: list[tuple[int, int]]


def _expected_mode(semaphore_state: SemaphoreState) -> str:
    return _PAPER if semaphore_state == SemaphoreState.NARANJA else _REAL


async def compute_drift(session: AsyncSession) -> list[ConfigDriftRow]:
    bots = (await session.execute(select(Bot))).scalars().all()
    rows: list[ConfigDriftRow] = []
    for bot in bots:
        ea_state = (
            await session.execute(
                select(EaState).where(
                    EaState.account_id == bot.account_id, EaState.magic_number == bot.magic_number
                )
            )
        ).scalar_one_or_none()
        if ea_state is None:
            continue

        expected = _expected_mode(bot.semaphore_state)
        reported = ea_state.mode.upper()
        rows.append(
            ConfigDriftRow(
                bot_id=bot.id,
                account_id=bot.account_id,
                magic_number=bot.magic_number,
                expected_mode=expected,
                reported_mode=reported,
                drift=expected != reported,
            )
        )
    return rows


async def compute_orphans_and_missing(session: AsyncSession) -> OrphanReport:
    bot_keys = {
        (account_id, magic_number)
        for account_id, magic_number in (
            await session.execute(select(Bot.account_id, Bot.magic_number))
        ).all()
    }
    ea_keys = {
        (account_id, magic_number)
        for account_id, magic_number in (
            await session.execute(select(EaState.account_id, EaState.magic_number))
        ).all()
    }
    return OrphanReport(
        orphan_magics=sorted(ea_keys - bot_keys),
        missing_magics=sorted(bot_keys - ea_keys),
    )


async def run_drift_check(session: AsyncSession, redis: Redis, now: datetime) -> None:
    rows = await compute_drift(session)
    for row in rows:
        dedup_key = f"config_drift:{row.bot_id}"
        existing = (
            await session.execute(
                select(Alert).where(Alert.dedup_key == dedup_key, Alert.resolved.is_(False))
            )
        ).scalar_one_or_none()

        if row.drift:
            if existing is None:
                alert = Alert(
                    ts=now,
                    level=AlertLevel.CRITICA,
                    module="config_drift",
                    message=(
                        f"Bot {row.bot_id} (magic {row.magic_number}): EA en modo incorrecto "
                        f"(esperado {row.expected_mode}, reportado {row.reported_mode})."
                    ),
                    action_required="Corregir el modo del EA en el terminal MT5.",
                    dedup_key=dedup_key,
                )
                session.add(alert)
                await session.flush()
                await redis.publish(
                    "events:alert",
                    json.dumps(
                        {
                            "type": "alert.created",
                            "ts": now.isoformat(),
                            "alert_id": alert.id,
                            "level": alert.level.value,
                            "module": alert.module,
                            "message": alert.message,
                            "dedup_key": alert.dedup_key,
                        }
                    ),
                )
        elif existing is not None:
            existing.resolved = True
            existing.resolved_at = now
            existing.resolved_by = "system:config_drift"
            await session.flush()
