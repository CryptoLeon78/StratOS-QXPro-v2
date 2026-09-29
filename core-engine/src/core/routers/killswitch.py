"""PARTE 9.2: `GET /api/v1/killswitch/status` + `POST /confirm` -- pestaña
Riesgo (7.7, "Drawdown y kill-switch") + `KillSwitchLadder`. `/confirm` es
la UNICA ruta de desescalado (P6.2: "desescalado solo manual con firma") --
el barrido automatico (`killswitch_sweep.py`) solo escala, nunca baja de
nivel."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.models.governance import User
from core.redis import get_redis
from core.routers.scope import AccountScope
from core.services.killswitch_sweep import (
    KillSwitchSweepConfig,
    compute_portfolio_dd_pct,
    current_episode_stats,
    current_killswitch_level,
)
from core.state_machines.killswitch import (
    apply_killswitch_transition,
    evaluate_killswitch_deescalation,
)
from core.state_machines.types import KillSwitchConfig

router = APIRouter(
    prefix="/api/v1/killswitch", tags=["killswitch"], dependencies=[Depends(get_current_user)]
)

_KS_CONFIG = KillSwitchConfig()
_SWEEP_CONFIG = KillSwitchSweepConfig()


class KillSwitchStatusResponse(BaseModel):
    level: int
    portfolio_dd_pct: Decimal | None
    instruction_text: str | None
    episode_max_dd_pct: Decimal | None
    episode_duration_seconds: float | None


async def _status(
    session: AsyncSession, now: datetime, account_id: int | None
) -> KillSwitchStatusResponse:
    level = await current_killswitch_level(session, account_id)
    dd_pct = await compute_portfolio_dd_pct(session, _SWEEP_CONFIG, now, account_id)
    instructions = {
        0: None,
        1: _KS_CONFIG.instruction_l1,
        2: _KS_CONFIG.instruction_l2,
        3: _KS_CONFIG.instruction_l3,
        4: _KS_CONFIG.instruction_l4,
    }
    episode = await current_episode_stats(session, now, account_id)
    return KillSwitchStatusResponse(
        level=level,
        portfolio_dd_pct=dd_pct,
        instruction_text=instructions[level],
        episode_max_dd_pct=episode.max_dd_pct if episode is not None else None,
        episode_duration_seconds=episode.duration.total_seconds() if episode is not None else None,
    )


@router.get("/status", response_model=KillSwitchStatusResponse)
async def killswitch_status(
    account_id: AccountScope,
    session: AsyncSession = Depends(get_session),
) -> KillSwitchStatusResponse:
    return await _status(session, datetime.now(UTC), account_id)


@router.post("/confirm", response_model=KillSwitchStatusResponse)
async def confirm_deescalation(
    account_id: AccountScope,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> KillSwitchStatusResponse:
    now = datetime.now(UTC)
    current_level = await current_killswitch_level(session, account_id)
    dd_pct = await compute_portfolio_dd_pct(session, _SWEEP_CONFIG, now, account_id) or Decimal("0")

    result = evaluate_killswitch_deescalation(
        dd_pct, current_level, _KS_CONFIG, signed_by=user.email
    )
    await apply_killswitch_transition(session, redis, result, account_id)
    await session.commit()
    return await _status(session, now, account_id)
