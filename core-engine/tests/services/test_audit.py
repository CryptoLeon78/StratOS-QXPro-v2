from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
from sqlalchemy import select

from core.db.enums import AlertLevel
from core.db.models.decisions import Alert
from core.services.audit import (
    AuditConfig,
    compute_reconciliation,
    compute_seals_summary,
    compute_send_continuity,
    run_audit_daily,
)
from tests.factories import (
    AccountFactory,
    BotFactory,
    EquitySnapshotFactory,
    IngestBatchFactory,
    TradeFactory,
)

CONFIG = AuditConfig()


async def _account(db_session: object) -> object:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account


class TestComputeReconciliation:
    async def test_matching_balance_has_zero_discrepancy(self, db_session: object) -> None:
        account = await _account(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=10), balance=Decimal("30000.00")
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(account_id=account.id, ts=now, balance=Decimal("30500.00"))
        )
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                close_time=now - timedelta(days=1),
                close_price=Decimal("1.1"),
                profit=Decimal("500.00"),
                commission=Decimal("0.00"),
                swap=Decimal("0.00"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await compute_reconciliation(db_session, account.id, CONFIG)  # type: ignore[arg-type]
        assert result is not None
        assert result.discrepancy_pct == Decimal("0")
        assert result.breached is False

    async def test_mismatched_balance_is_breached(self, db_session: object) -> None:
        account = await _account(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=10), balance=Decimal("30000.00")
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(account_id=account.id, ts=now, balance=Decimal("35000.00"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await compute_reconciliation(db_session, account.id, CONFIG)  # type: ignore[arg-type]
        assert result is not None
        assert result.breached is True
        assert result.discrepancy_pct is not None
        assert result.discrepancy_pct > 0

    async def test_returns_none_without_at_least_two_snapshots(self, db_session: object) -> None:
        account = await _account(db_session)
        result = await compute_reconciliation(db_session, account.id, CONFIG)  # type: ignore[arg-type]
        assert result is None


class TestComputeSendContinuity:
    async def test_dense_heartbeats_within_threshold_report_no_gaps(
        self, db_session: object
    ) -> None:
        from core.db.models.market import HeartbeatLog

        account = await _account(db_session)
        now = datetime.now(UTC)
        # cada 2 minutos durante 1h -- por debajo del umbral de 5 min
        # (heartbeat_gap_threshold_s), nunca cuenta como tramo sin envio.
        for minutes_ago in range(60, -1, -2):
            db_session.add(  # type: ignore[attr-defined]
                HeartbeatLog(
                    ts=now - timedelta(minutes=minutes_ago),
                    connector_instance_id="c1",
                    account_id=account.id,
                    latency_ms=50,
                    status="ok",
                )
            )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await compute_send_continuity(  # type: ignore[arg-type]
            db_session, account.id, CONFIG, days=1, now=now
        )
        assert result.gaps == []

    async def test_a_gap_is_reported(self, db_session: object) -> None:
        from core.db.models.market import HeartbeatLog

        account = await _account(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            HeartbeatLog(
                ts=now - timedelta(hours=5),
                connector_instance_id="c1",
                account_id=account.id,
                latency_ms=50,
                status="ok",
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            HeartbeatLog(
                ts=now - timedelta(hours=1),
                connector_instance_id="c1",
                account_id=account.id,
                latency_ms=50,
                status="ok",
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await compute_send_continuity(db_session, account.id, CONFIG, days=1, now=now)  # type: ignore[arg-type]
        assert len(result.gaps) == 1
        assert result.gaps[0].duration_minutes == 240.0


class TestComputeSealsSummary:
    async def test_counts_batches_and_trades(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                ticket_mt5=3000500,
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        summary = await compute_seals_summary(db_session)  # type: ignore[arg-type]
        assert summary.total_batches >= 1
        assert summary.total_trades >= 1


class TestRunAuditDaily:
    async def test_breach_creates_critica_alert(self, db_session: object) -> None:
        account = await _account(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=10), balance=Decimal("30000.00")
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(account_id=account.id, ts=now, balance=Decimal("99999.00"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        await run_audit_daily(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alert = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(Alert).where(Alert.dedup_key == f"audit:{account.id}")
            )
        ).scalar_one()
        assert alert.level == AlertLevel.CRITICA
        await redis.aclose()
