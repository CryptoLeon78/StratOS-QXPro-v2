"""G10 (docs/backlog.md): cruza `Trade` YA ejecutados contra las ventanas
de exclusion de `NewsEvent` (`ts +/- blackout_before/after_min`), por la
divisa del simbolo del trade (`symbol_currency`, G10 tambien) --
retrospectivo, para auditar si el sistema opero durante una ventana que
deberia haber evitado. Distinto de `routers/news.py::_shield_rows`, que
mira hacia ADELANTE ("bots afectados" via `Bot.market`, sin cruzar contra
trades reales)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Bot
from core.db.models.governance import NewsEvent
from core.db.models.market import SymbolCurrency, Trade


@dataclass(frozen=True)
class TradeInNewsWindow:
    trade_id: int
    symbol: str
    bot_name: str | None
    open_time: datetime
    close_time: datetime | None
    news_event_id: int
    news_title: str
    news_ts: datetime


async def trades_in_news_window(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
    account_id: int | None = None,
) -> list[TradeInNewsWindow]:
    """Trades cuyo intervalo `[open_time, close_time o ahora]` se solapa
    con la ventana de exclusion de un `NewsEvent` de la misma divisa (via
    `symbol_currency`) -- solo eventos con `ts` en `[window_start,
    window_end]` (p.ej. ultimos 30 dias). Un trade cuyo simbolo no tiene
    fila en `symbol_currency` se excluye: no se puede saber que divisa
    vigilar, no se inventa."""
    events = (
        (
            await session.execute(
                select(NewsEvent).where(NewsEvent.ts >= window_start, NewsEvent.ts <= window_end)
            )
        )
        .scalars()
        .all()
    )
    if not events:
        return []

    currencies = {event.currency for event in events}
    symbol_rows = (
        await session.execute(
            select(SymbolCurrency.symbol, SymbolCurrency.currency).where(
                SymbolCurrency.currency.in_(currencies)
            )
        )
    ).all()
    if not symbol_rows:
        return []
    currency_by_symbol = {symbol: currency for symbol, currency in symbol_rows}

    trades_query = (
        select(Trade, Bot.name)
        .outerjoin(Bot, Bot.id == Trade.bot_id)
        .where(Trade.symbol.in_(currency_by_symbol.keys()), Trade.open_time <= window_end)
    )
    if account_id is not None:
        trades_query = trades_query.where(Trade.account_id == account_id)
    trades = (await session.execute(trades_query)).all()

    now = datetime.now(UTC)
    matches: list[TradeInNewsWindow] = []
    for trade, bot_name in trades:
        currency = currency_by_symbol[trade.symbol]
        trade_end = trade.close_time or now
        for event in events:
            if event.currency != currency:
                continue
            win_start = event.ts - timedelta(minutes=event.blackout_before_min)
            win_end = event.ts + timedelta(minutes=event.blackout_after_min)
            if trade.open_time <= win_end and trade_end >= win_start:
                matches.append(
                    TradeInNewsWindow(
                        trade_id=trade.id,
                        symbol=trade.symbol,
                        bot_name=bot_name,
                        open_time=trade.open_time,
                        close_time=trade.close_time,
                        news_event_id=event.id,
                        news_title=event.title,
                        news_ts=event.ts,
                    )
                )

    return matches
