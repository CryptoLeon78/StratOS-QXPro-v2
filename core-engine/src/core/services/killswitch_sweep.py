"""PARTE 6.2: barrido periodico del kill-switch de portfolio. Ensambla el
drawdown REAL de portfolio (solo cuentas REALES, nunca DEMO -- P6.2) con la
curva de equity agregada (reutiliza `risk.py::real_portfolio_equity_curve`)
y delega en `evaluate_killswitch_escalation`/`apply_killswitch_transition`
(state_machines/killswitch.py, G3, ya existen). Solo evalua ESCALADA
automatica -- el desescalado exige firma humana, vive en la ruta
`POST /killswitch/confirm` (routers/, capa API), no en un barrido."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.decisions import KillSwitchEvent
from core.services.risk import real_portfolio_equity_curve
from core.state_machines.killswitch import (
    apply_killswitch_transition,
    evaluate_killswitch_escalation,
)
from core.state_machines.types import KillSwitchConfig


@dataclass(frozen=True)
class KillSwitchSweepConfig:
    # "todo el historial disponible" para localizar el pico real de equity,
    # no una ventana corta -- el DD de kill-switch se mide desde el maximo
    # historico, no desde un maximo local reciente (ASSUMPTIONS G5).
    equity_lookback_days: int = 3650


async def compute_portfolio_dd_pct(
    session: AsyncSession, config: KillSwitchSweepConfig, now: datetime
) -> Decimal | None:
    equity_curve = await real_portfolio_equity_curve(
        session, now - timedelta(days=config.equity_lookback_days)
    )
    if equity_curve.empty:
        return None
    peak = float(equity_curve.max())
    if peak <= 0:
        return None
    current = float(equity_curve.iloc[-1])
    return Decimal(str((peak - current) / peak * 100))


async def current_killswitch_level(session: AsyncSession) -> int:
    last = (
        await session.execute(
            select(KillSwitchEvent.level).order_by(KillSwitchEvent.ts.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return last if last is not None else 0


@dataclass(frozen=True)
class KillSwitchEpisodeStats:
    max_dd_pct: Decimal
    started_at: datetime
    duration: timedelta


async def current_episode_stats(
    session: AsyncSession, now: datetime
) -> KillSwitchEpisodeStats | None:
    """G10 (docs/backlog.md): MAX DD y DURACION del episodio de
    kill-switch ACTIVO -- la racha ininterrumpida de eventos `level>0` mas
    reciente, terminando en el ultimo evento y empezando justo despues del
    ultimo desescalado a `level=0` (o desde el principio del historial, si
    nunca hubo uno). Nivel actual 0, o sin eventos -- sin episodio activo,
    `None`."""
    events = (
        (await session.execute(select(KillSwitchEvent).order_by(KillSwitchEvent.ts.desc())))
        .scalars()
        .all()
    )
    if not events or events[0].level == 0:
        return None

    episode = []
    for event in events:
        if event.level == 0:
            break
        episode.append(event)

    max_dd_pct = max(event.portfolio_dd_pct for event in episode)
    started_at = min(event.ts for event in episode)
    return KillSwitchEpisodeStats(
        max_dd_pct=max_dd_pct, started_at=started_at, duration=now - started_at
    )


async def sweep_portfolio(
    session: AsyncSession,
    redis: Redis,
    config: KillSwitchConfig,
    sweep_config: KillSwitchSweepConfig,
    now: datetime,
) -> None:
    dd_pct = await compute_portfolio_dd_pct(session, sweep_config, now)
    if dd_pct is None:
        return

    current_level = await current_killswitch_level(session)
    result = evaluate_killswitch_escalation(dd_pct, current_level, config)
    await apply_killswitch_transition(session, redis, result)
