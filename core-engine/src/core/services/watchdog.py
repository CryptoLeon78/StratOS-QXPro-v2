"""PARTE 7.6/7.8: watchdog de bots (frecuencia observada vs esperada, 30
dias) + drift horario del VPS. `watchdog_deviation()` (formulas/monitoring.py,
G2) es pura; este modulo la envuelve con datos reales (Bot/Baseline/Trade) y
persiste el resultado como Alert, mismo patron de dedup/resolve que P5
(ingest/services/positions.py, G4)."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AlertLevel
from core.db.models.accounts import Baseline, Bot
from core.db.models.decisions import Alert
from core.db.models.market import Trade
from core.formulas.monitoring import watchdog_deviation
from core.formulas.types import WatchdogState

_WATCHDOG_WINDOW_DAYS = 30
_CLOCK_DRIFT_DEDUP_KEY = "watchdog:vps_clock_drift"

# Estados que ameritan Alert -- OK/INSUFFICIENT_DATA nunca alertan (7.8:
# "baseline sin frecuencia esperada -> INSUFFICIENT_DATA (sin alerta)").
# DEAD/RUNAWAY son mas graves (bot inactivo o fuera de control) que
# OUT_OF_TOLERANCE (desviacion dentro de un orden de magnitud) -- diseno
# propio, ASSUMPTIONS G5.
_CRITICAL_STATES = {WatchdogState.DEAD, WatchdogState.RUNAWAY}
_SOFT_STATES = {WatchdogState.OUT_OF_TOLERANCE}


@dataclass(frozen=True)
class WatchdogServiceConfig:
    tolerance: float = 0.25
    runaway_factor: float = 3.0


@dataclass(frozen=True)
class WatchdogRow:
    bot_id: int
    magic_number: int
    state: WatchdogState
    observed_30d: int
    expected_month: int | None
    last_trade_at: datetime | None


def _dedup_key(bot_id: int) -> str:
    return f"watchdog:{bot_id}"


async def _publish_alert_event(redis: Redis, event_type: str, alert: Alert) -> None:
    await redis.publish(
        "events:alert",
        json.dumps(
            {
                "type": event_type,
                "ts": alert.ts.isoformat(),
                "alert_id": alert.id,
                "level": alert.level.value,
                "module": alert.module,
                "message": alert.message,
                "dedup_key": alert.dedup_key,
            }
        ),
    )


async def evaluate_all_bots(
    session: AsyncSession, config: WatchdogServiceConfig, now: datetime
) -> list[WatchdogRow]:
    bots = (await session.execute(select(Bot))).scalars().all()
    window_start = now - timedelta(days=_WATCHDOG_WINDOW_DAYS)
    rows: list[WatchdogRow] = []
    for bot in bots:
        observed = (
            await session.execute(
                select(func.count(Trade.id)).where(
                    Trade.bot_id == bot.id, Trade.open_time >= window_start
                )
            )
        ).scalar_one()
        expected: int | None = None
        if bot.baseline_id is not None:
            expected = (
                await session.execute(
                    select(Baseline.expected_trades_30d).where(Baseline.id == bot.baseline_id)
                )
            ).scalar_one_or_none()
        last_trade_at = (
            await session.execute(select(func.max(Trade.open_time)).where(Trade.bot_id == bot.id))
        ).scalar_one_or_none()

        state = watchdog_deviation(
            observed=float(observed),
            expected=float(expected) if expected is not None else None,
            tolerance=config.tolerance,
            runaway_factor=config.runaway_factor,
        )
        rows.append(
            WatchdogRow(
                bot_id=bot.id,
                magic_number=bot.magic_number,
                state=state,
                observed_30d=observed,
                expected_month=expected,
                last_trade_at=last_trade_at,
            )
        )
    return rows


async def run_watchdog_sweep(
    session: AsyncSession, redis: Redis, config: WatchdogServiceConfig, now: datetime
) -> None:
    rows = await evaluate_all_bots(session, config, now)
    for row in rows:
        dedup_key = _dedup_key(row.bot_id)
        existing = (
            await session.execute(
                select(Alert).where(Alert.dedup_key == dedup_key, Alert.resolved.is_(False))
            )
        ).scalar_one_or_none()

        if row.state in _CRITICAL_STATES or row.state in _SOFT_STATES:
            if existing is None:
                level = AlertLevel.CRITICA if row.state in _CRITICAL_STATES else AlertLevel.SUAVE
                alert = Alert(
                    ts=now,
                    level=level,
                    module="watchdog",
                    message=(
                        f"Bot {row.bot_id} (magic {row.magic_number}): watchdog {row.state.value} "
                        f"(observado {row.observed_30d}, esperado {row.expected_month})."
                    ),
                    action_required="Revisar el bot en el terminal MT5.",
                    dedup_key=dedup_key,
                )
                session.add(alert)
                await session.flush()
                await _publish_alert_event(redis, "alert.created", alert)
        elif existing is not None:
            existing.resolved = True
            existing.resolved_at = now
            existing.resolved_by = "system:watchdog"
            await session.flush()
            await _publish_alert_event(redis, "alert.resolved", existing)


async def check_vps_clock_drift(
    session: AsyncSession, redis: Redis, drift_s: int, now: datetime, threshold_s: int = 120
) -> None:
    """7.8, caso limite explicito: drift horario VPS >120s -> SUAVE."""
    existing = (
        await session.execute(
            select(Alert).where(
                Alert.dedup_key == _CLOCK_DRIFT_DEDUP_KEY, Alert.resolved.is_(False)
            )
        )
    ).scalar_one_or_none()

    if drift_s > threshold_s:
        if existing is None:
            alert = Alert(
                ts=now,
                level=AlertLevel.SUAVE,
                module="watchdog",
                message=f"Drift horario del VPS de {drift_s}s (umbral {threshold_s}s).",
                action_required="Resincronizar el reloj del VPS.",
                dedup_key=_CLOCK_DRIFT_DEDUP_KEY,
            )
            session.add(alert)
            await session.flush()
            await _publish_alert_event(redis, "alert.created", alert)
    elif existing is not None:
        existing.resolved = True
        existing.resolved_at = now
        existing.resolved_by = "system:watchdog"
        await session.flush()
        await _publish_alert_event(redis, "alert.resolved", existing)
