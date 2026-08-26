"""PARTE 9.2: `GET /api/v1/news/shield` + `/shield/windows` -- pestaña
Riesgo (7.7, "News Shield"). Las ventanas de exclusion son
`[ts - blackout_before_min, ts + blackout_after_min]` (NewsEvent, ya
migrada en G1); "bots afectados" = bots cuyo `market` contiene la divisa
del evento (heuristica simple: EURUSD contiene EUR y USD)."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.dependencies import get_current_user
from core.db.base import get_session
from core.db.enums import NewsImpact
from core.db.models.accounts import Bot
from core.db.models.governance import NewsEvent

router = APIRouter(prefix="/api/v1/news", tags=["news"], dependencies=[Depends(get_current_user)])


class NewsShieldRow(BaseModel):
    id: int
    ts: datetime
    currency: str
    impact: NewsImpact
    title: str
    source: str
    window_start: datetime
    window_end: datetime
    affected_bots: list[str]


async def _shield_rows(session: AsyncSession, hours: int) -> list[NewsShieldRow]:
    now = datetime.now(UTC)
    end = now + timedelta(hours=hours)
    events = (
        (
            await session.execute(
                select(NewsEvent)
                .where(NewsEvent.ts >= now, NewsEvent.ts <= end)
                .order_by(NewsEvent.ts)
            )
        )
        .scalars()
        .all()
    )
    bots = (await session.execute(select(Bot.name, Bot.market))).all()

    rows = []
    for event in events:
        affected = [name for name, market in bots if event.currency in market]
        rows.append(
            NewsShieldRow(
                id=event.id,
                ts=event.ts,
                currency=event.currency,
                impact=event.impact,
                title=event.title,
                source=event.source,
                window_start=event.ts - timedelta(minutes=event.blackout_before_min),
                window_end=event.ts + timedelta(minutes=event.blackout_after_min),
                affected_bots=affected,
            )
        )
    return rows


@router.get("/shield", response_model=list[NewsShieldRow])
async def news_shield(
    hours: int = Query(default=48), session: AsyncSession = Depends(get_session)
) -> list[NewsShieldRow]:
    return await _shield_rows(session, hours)


@router.get("/shield/windows", response_model=None)
async def news_shield_windows(
    hours: int = Query(default=48),
    format_: Literal["text", "csv", "json"] = Query(default="text", alias="format"),
    session: AsyncSession = Depends(get_session),
) -> PlainTextResponse | list[NewsShieldRow]:
    rows = await _shield_rows(session, hours)
    if format_ == "json":
        return rows
    if format_ == "csv":
        lines = ["start,end,currency,title"]
        lines += [
            f"{r.window_start.isoformat()},{r.window_end.isoformat()},{r.currency},{r.title}"
            for r in rows
        ]
        return PlainTextResponse("\n".join(lines), media_type="text/csv")
    lines = [
        f"{r.window_start.strftime('%Y-%m-%d %H:%M')} - {r.window_end.strftime('%Y-%m-%d %H:%M')} "
        f"UTC ({r.currency}, {r.title})"
        for r in rows
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain")
