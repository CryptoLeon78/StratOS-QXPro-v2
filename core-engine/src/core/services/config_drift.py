"""PARTE 7.2 ("Panel Deriva de configuracion", diseño derivado sin captura)
+ criterio de salida literal de G5 ("deriva EA modo incorrecto"). Compara
el modo esperado (derivado de `Bot.semaphore_state`: NARANJA -> PAPER,
cualquier otro -> REAL) contra `EaState.mode` (G4, ultimo estado reportado).

Deriva de SIZING (G10, docs/backlog.md): `EaState.sizing_pct` (columna
nueva, opcional) vs `Bot.sizing_current_pct`. El conector/EA real NO
manda `sizing_pct` todavia (`mt5-connector/src/connector/protocol.py`,
sin cambios en G10) -- `sizing_drift` queda en `None` (no comparable, ni
"sin deriva") mientras el EA no lo reporte, nunca se inventa una
comparacion contra un dato ausente. Backend construido a spec, no
verificado contra hardware real (mismo patron que G4)."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AlertLevel, BotOriginKind, SemaphoreState
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
    expected_autotrading: bool
    reported_autotrading: bool
    autotrading_drift: bool
    expected_sizing_pct: Decimal
    reported_sizing_pct: Decimal | None
    sizing_drift: bool | None


@dataclass(frozen=True)
class OrphanReport:
    orphan_magics: list[tuple[int, int]]
    missing_magics: list[tuple[int, int]]


def _expected_mode(bot: Bot, now: datetime) -> str:
    """La gracia de incubacion es explicita y no convierte un F3 en VERDE.

    Durante ella el EA demo debe poder generar OOS real; fuera de ese intervalo
    vuelve a regir exclusivamente el semaforo persistido.
    """
    if (
        bot.origin_kind == BotOriginKind.INCUBATION
        and bot.incubation_grace_until is not None
        and now < bot.incubation_grace_until
    ):
        return _REAL
    semaphore_state = bot.semaphore_state
    return _PAPER if semaphore_state == SemaphoreState.NARANJA else _REAL


async def compute_drift(session: AsyncSession) -> list[ConfigDriftRow]:
    bots = (await session.execute(select(Bot))).scalars().all()
    now = datetime.now(UTC)
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

        expected = _expected_mode(bot, now)
        reported = ea_state.mode.upper()
        reported_sizing = ea_state.sizing_pct
        sizing_drift = (
            reported_sizing != bot.sizing_current_pct if reported_sizing is not None else None
        )
        rows.append(
            ConfigDriftRow(
                bot_id=bot.id,
                account_id=bot.account_id,
                magic_number=bot.magic_number,
                expected_mode=expected,
                reported_mode=reported,
                drift=expected != reported,
                expected_autotrading=expected == _REAL,
                reported_autotrading=ea_state.autotrading,
                autotrading_drift=ea_state.autotrading != (expected == _REAL),
                expected_sizing_pct=bot.sizing_current_pct,
                reported_sizing_pct=reported_sizing,
                sizing_drift=sizing_drift,
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

        has_drift = row.drift or row.autotrading_drift or row.sizing_drift is True
        if has_drift:
            if existing is None:
                details: list[str] = []
                if row.drift:
                    details.append(
                        "modo incorrecto "
                        f"(esperado {row.expected_mode}, reportado {row.reported_mode})"
                    )
                if row.autotrading_drift:
                    details.append(
                        "permiso AutoTrading incorrecto "
                        f"(esperado {row.expected_autotrading}, "
                        f"reportado {row.reported_autotrading})"
                    )
                if row.sizing_drift is True:
                    details.append(
                        "sizing incorrecto "
                        f"(esperado {row.expected_sizing_pct}, reportado {row.reported_sizing_pct})"
                    )
                alert = Alert(
                    ts=now,
                    level=AlertLevel.CRITICA,
                    module="config_drift",
                    message=f"Bot {row.bot_id} (magic {row.magic_number}): "
                    + "; ".join(details)
                    + ".",
                    action_required="Corregir el contrato operativo del EA en el terminal MT5.",
                    dedup_key=dedup_key,
                    account_id=row.account_id,
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
