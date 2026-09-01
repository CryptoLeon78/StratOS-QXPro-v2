from datetime import UTC, datetime
from decimal import Decimal

from core.db.enums import TradeType
from core.db.models.market import ExecutionFill
from core.services.tca import tca_summary
from tests.factories import AccountFactory, IngestBatchFactory


async def test_tca_uses_signed_slippage_and_exposes_broker_profile(db_session: object) -> None:
    session = db_session
    account = AccountFactory(broker="Darwinex")
    session.add(account)
    await session.flush()
    batch = IngestBatchFactory(account_id=account.id, batch_type="execution")
    session.add(batch)
    await session.flush()
    session.add_all(
        [
            ExecutionFill(
                account_id=account.id,
                bot_id=None,
                magic_number=118231,
                order_id="buy-adverse",
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("0.10"),
                requested_price=Decimal("1.1000"),
                executed_price=Decimal("1.1002"),
                spread=Decimal("0.0002"),
                ts=datetime.now(UTC),
                ingest_batch_id=batch.id,
            ),
            ExecutionFill(
                account_id=account.id,
                bot_id=None,
                magic_number=118231,
                order_id="sell-adverse",
                symbol="EURUSD",
                type=TradeType.SELL,
                volume=Decimal("0.10"),
                requested_price=Decimal("1.1000"),
                executed_price=Decimal("1.1002"),
                spread=Decimal("0.0002"),
                ts=datetime.now(UTC),
                ingest_batch_id=batch.id,
            ),
            ExecutionFill(
                account_id=account.id,
                bot_id=None,
                magic_number=118231,
                order_id="rejected",
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("0.10"),
                requested_price=Decimal("1.1000"),
                status="REJECTED",
                rejection_reason="MARKET_CLOSED",
                executed_price=None,
                spread=None,
                ts=datetime.now(UTC),
                ingest_batch_id=batch.id,
            ),
        ]
    )
    await session.flush()

    summary = await tca_summary(session)

    assert summary is not None
    assert summary.fills == 2
    assert summary.rejected_orders == 1
    assert summary.slippage_p50 == Decimal("0.0")
    assert summary.broker_profiles[0].broker == "Darwinex"
    assert summary.broker_profiles[0].spread_p50 == Decimal("0.0002")


async def test_tca_does_not_invent_metrics_for_rejections_only(db_session: object) -> None:
    session = db_session
    account = AccountFactory()
    session.add(account)
    await session.flush()
    batch = IngestBatchFactory(account_id=account.id, batch_type="execution")
    session.add(batch)
    await session.flush()
    session.add(
        ExecutionFill(
            account_id=account.id,
            bot_id=None,
            magic_number=118231,
            order_id="only-rejected",
            symbol="EURUSD",
            type=TradeType.BUY,
            volume=Decimal("0.10"),
            requested_price=Decimal("1.1000"),
            status="REJECTED",
            rejection_reason="MARKET_CLOSED",
            executed_price=None,
            spread=None,
            ts=datetime.now(UTC),
            ingest_batch_id=batch.id,
        )
    )
    await session.flush()

    summary = await tca_summary(session)

    assert summary is not None
    assert summary.fills == 0
    assert summary.rejected_orders == 1
    assert summary.slippage_p50 is None
