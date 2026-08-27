"""G10 (docs/backlog.md): `trades_in_news_window` cruza `Trade` YA
ejecutados contra las ventanas de exclusion de `NewsEvent`, por la divisa
del simbolo (`symbol_currency`, G10 tambien) -- distinto de
`routers/news.py::_shield_rows` (que mira "bots afectados" hacia ADELANTE
via `Bot.market`); esto es retrospectivo, para auditar si el sistema
opero durante una ventana que deberia haber evitado."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from core.db.enums import NewsImpact, TradeType
from core.db.models.governance import NewsEvent
from core.services.news import trades_in_news_window
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory


async def _bot(db_session: object) -> object:
    account = AccountFactory()  # type: ignore[call-arg]
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id)  # type: ignore[call-arg]
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)  # type: ignore[call-arg]
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return bot, account, batch


def _event(ts: datetime, currency: str = "EUR") -> NewsEvent:
    return NewsEvent(
        ts=ts,
        currency=currency,
        impact=NewsImpact.HIGH,
        title="NFP",
        source="test",
        blackout_before_min=30,
        blackout_after_min=30,
    )


async def test_flags_a_trade_open_during_the_news_window(db_session: object) -> None:
    bot, account, batch = await _bot(db_session)
    news_ts = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    db_session.add(_event(news_ts))  # type: ignore[attr-defined]
    db_session.add(  # type: ignore[attr-defined]
        TradeFactory(
            bot_id=bot.id,
            account_id=account.id,
            magic_number=bot.magic_number,
            symbol="EURUSD",
            type=TradeType.BUY,
            volume=Decimal("1.00"),
            profit=Decimal("10.00"),
            open_time=news_ts - timedelta(minutes=10),  # dentro de la ventana [-30,+30]
            close_time=news_ts + timedelta(minutes=5),
            close_price=Decimal("1.1"),
            ingest_batch_id=batch.id,
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]

    matches = await trades_in_news_window(  # type: ignore[arg-type]
        db_session, window_start=news_ts - timedelta(days=1), window_end=news_ts + timedelta(days=1)
    )
    assert len(matches) == 1
    assert matches[0].symbol == "EURUSD"
    assert matches[0].news_title == "NFP"


async def test_ignores_a_trade_entirely_outside_the_window(db_session: object) -> None:
    bot, account, batch = await _bot(db_session)
    news_ts = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    db_session.add(_event(news_ts))  # type: ignore[attr-defined]
    db_session.add(  # type: ignore[attr-defined]
        TradeFactory(
            bot_id=bot.id,
            account_id=account.id,
            magic_number=bot.magic_number,
            symbol="EURUSD",
            type=TradeType.BUY,
            volume=Decimal("1.00"),
            profit=Decimal("10.00"),
            open_time=news_ts - timedelta(hours=5),
            close_time=news_ts - timedelta(hours=4),
            close_price=Decimal("1.1"),
            ingest_batch_id=batch.id,
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]

    matches = await trades_in_news_window(  # type: ignore[arg-type]
        db_session, window_start=news_ts - timedelta(days=1), window_end=news_ts + timedelta(days=1)
    )
    assert matches == []


async def test_ignores_a_trade_of_an_unrelated_currency(db_session: object) -> None:
    bot, account, batch = await _bot(db_session)
    news_ts = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    db_session.add(_event(news_ts, currency="JPY"))  # type: ignore[attr-defined]
    db_session.add(  # type: ignore[attr-defined]
        TradeFactory(
            bot_id=bot.id,
            account_id=account.id,
            magic_number=bot.magic_number,
            symbol="EURUSD",  # EUR/USD, no JPY
            type=TradeType.BUY,
            volume=Decimal("1.00"),
            profit=Decimal("10.00"),
            open_time=news_ts,
            close_time=news_ts + timedelta(minutes=1),
            close_price=Decimal("1.1"),
            ingest_batch_id=batch.id,
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]

    matches = await trades_in_news_window(  # type: ignore[arg-type]
        db_session, window_start=news_ts - timedelta(days=1), window_end=news_ts + timedelta(days=1)
    )
    assert matches == []


async def test_an_open_position_counts_as_active_until_now(db_session: object) -> None:
    bot, account, batch = await _bot(db_session)
    news_ts = datetime.now(UTC) - timedelta(minutes=5)  # ventana reciente, trade sigue abierto
    db_session.add(_event(news_ts))  # type: ignore[attr-defined]
    db_session.add(  # type: ignore[attr-defined]
        TradeFactory(
            bot_id=bot.id,
            account_id=account.id,
            magic_number=bot.magic_number,
            symbol="EURUSD",
            type=TradeType.BUY,
            volume=Decimal("1.00"),
            profit=Decimal("10.00"),
            open_time=news_ts - timedelta(hours=2),  # abierta bastante antes
            close_time=None,  # sigue abierta -> "activa hasta ahora"
            ingest_batch_id=batch.id,
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]

    matches = await trades_in_news_window(  # type: ignore[arg-type]
        db_session, window_start=news_ts - timedelta(days=1), window_end=news_ts + timedelta(days=1)
    )
    assert len(matches) == 1


async def test_only_matches_the_event_of_the_trades_own_currency(db_session: object) -> None:
    bot, account, batch = await _bot(db_session)
    news_ts = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    db_session.add(_event(news_ts, currency="EUR"))  # type: ignore[attr-defined]
    db_session.add(_event(news_ts, currency="GBP"))  # type: ignore[attr-defined]
    db_session.add(  # type: ignore[attr-defined]
        TradeFactory(
            bot_id=bot.id,
            account_id=account.id,
            magic_number=bot.magic_number,
            symbol="EURUSD",  # divisa EUR, no GBP
            type=TradeType.BUY,
            volume=Decimal("1.00"),
            profit=Decimal("10.00"),
            open_time=news_ts,
            close_time=news_ts + timedelta(minutes=1),
            close_price=Decimal("1.1"),
            ingest_batch_id=batch.id,
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]

    matches = await trades_in_news_window(  # type: ignore[arg-type]
        db_session, window_start=news_ts - timedelta(days=1), window_end=news_ts + timedelta(days=1)
    )
    assert len(matches) == 1
    assert matches[0].news_event_id is not None


async def test_no_events_in_range_returns_empty(db_session: object) -> None:
    now = datetime.now(UTC)
    matches = await trades_in_news_window(  # type: ignore[arg-type]
        db_session, window_start=now - timedelta(days=1), window_end=now
    )
    assert matches == []
