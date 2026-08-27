from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
import pytest
from sqlalchemy import select

from core.db.enums import TradeType
from core.db.models.decisions import Alert
from core.db.models.governance import UmsPhaseLog
from core.services.ums import (
    DEFAULT_UMS_PHASES,
    UmsConfig,
    UmsCurrentState,
    UmsMetrics,
    check_automatic_downgrade,
    confirm_advance,
    current_phase,
    evaluate_advance_readiness,
    monthly_evolution_metrics,
)
from tests.factories import (
    AccountFactory,
    BotFactory,
    EquitySnapshotFactory,
    IngestBatchFactory,
    TradeFactory,
)

CONFIG = UmsConfig(min_months=3, min_sharpe=1.0, max_dd_gate_pct=Decimal("8"))
GOOD_METRICS = UmsMetrics(sharpe=1.5, dd_pct=Decimal("3"))


class TestEvaluateAdvanceReadiness:
    def test_ready_when_all_conditions_met(self) -> None:
        now = datetime(2026, 6, 1, tzinfo=UTC)
        current = UmsCurrentState(phase=2, entered_at=now - timedelta(days=100))
        readiness = evaluate_advance_readiness(current, GOOD_METRICS, CONFIG, now)
        assert readiness.ready_to_advance is True

    def test_not_ready_when_too_few_months_in_phase(self) -> None:
        now = datetime(2026, 6, 1, tzinfo=UTC)
        current = UmsCurrentState(phase=2, entered_at=now - timedelta(days=10))
        readiness = evaluate_advance_readiness(current, GOOD_METRICS, CONFIG, now)
        assert readiness.ready_to_advance is False

    def test_not_ready_when_sharpe_below_gate(self) -> None:
        now = datetime(2026, 6, 1, tzinfo=UTC)
        current = UmsCurrentState(phase=2, entered_at=now - timedelta(days=100))
        readiness = evaluate_advance_readiness(
            current, UmsMetrics(sharpe=0.5, dd_pct=Decimal("3")), CONFIG, now
        )
        assert readiness.ready_to_advance is False

    def test_not_ready_when_dd_breaches_gate(self) -> None:
        now = datetime(2026, 6, 1, tzinfo=UTC)
        current = UmsCurrentState(phase=2, entered_at=now - timedelta(days=100))
        readiness = evaluate_advance_readiness(
            current, UmsMetrics(sharpe=1.5, dd_pct=Decimal("9")), CONFIG, now
        )
        assert readiness.ready_to_advance is False

    def test_no_current_state_is_never_ready(self) -> None:
        now = datetime(2026, 6, 1, tzinfo=UTC)
        readiness = evaluate_advance_readiness(None, GOOD_METRICS, CONFIG, now)
        assert readiness.ready_to_advance is False


class TestConfirmAdvance:
    async def test_persists_signed_advance(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            UmsPhaseLog(
                ts=now - timedelta(days=100),
                phase=2,
                equity_at=Decimal("20000"),
                metrics={},
                ready_to_advance=False,
                signed_by=None,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await confirm_advance(
            db_session,
            GOOD_METRICS,
            CONFIG,
            "ivan",
            Decimal("30000"),
            now,  # type: ignore[arg-type]
        )
        assert result.phase == 3
        assert result.signed_by == "ivan"

    async def test_raises_when_not_ready(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            UmsPhaseLog(
                ts=now - timedelta(days=1),
                phase=2,
                equity_at=Decimal("20000"),
                metrics={},
                ready_to_advance=False,
                signed_by=None,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        with pytest.raises(ValueError, match="no cumple"):
            await confirm_advance(
                db_session,
                GOOD_METRICS,
                CONFIG,
                "ivan",
                Decimal("30000"),
                now,  # type: ignore[arg-type]
            )


class TestCheckAutomaticDowngrade:
    async def test_equity_drop_inserts_unsigned_downgrade_and_alerts(
        self, db_session: object
    ) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            UmsPhaseLog(
                ts=now - timedelta(days=10),
                phase=4,
                equity_at=Decimal("150000"),
                metrics={},
                ready_to_advance=False,
                signed_by="ivan",
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        await check_automatic_downgrade(db_session, redis, CONFIG, Decimal("20000"), now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        latest = await current_phase(db_session)  # type: ignore[arg-type]
        assert latest is not None
        assert latest.phase == 2
        assert latest.signed_by is None

        alert = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(Alert).where(Alert.module == "ums")
            )
        ).scalar_one()
        assert alert.dedup_key is not None
        await redis.aclose()

    async def test_equity_within_current_phase_does_nothing(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            UmsPhaseLog(
                ts=now - timedelta(days=10),
                phase=4,
                equity_at=Decimal("150000"),
                metrics={},
                ready_to_advance=False,
                signed_by="ivan",
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        await check_automatic_downgrade(db_session, redis, CONFIG, Decimal("200000"), now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        rows = (
            (await db_session.execute(select(UmsPhaseLog)))  # type: ignore[attr-defined]
            .scalars()
            .all()
        )
        assert len(rows) == 1
        await redis.aclose()


def test_default_phases_cover_the_six_contractual_bands() -> None:
    assert [p.phase for p in DEFAULT_UMS_PHASES] == [1, 2, 3, 4, 5, 6]


class TestMonthlyEvolutionMetrics:
    async def test_computes_trades_return_and_max_dd_over_the_last_month(
        self, db_session: object
    ) -> None:
        account = AccountFactory(is_demo=False)  # type: ignore[call-arg]
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id)  # type: ignore[call-arg]
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        batch = IngestBatchFactory(account_id=account.id)  # type: ignore[call-arg]
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=25), equity=Decimal("100000")
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=10), equity=Decimal("90000")
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(account_id=account.id, ts=now, equity=Decimal("110000"))
        )
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("10.00"),
                close_time=now - timedelta(days=5),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("999.00"),
                close_time=now - timedelta(days=40),  # fuera de la ventana de 1 mes
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await monthly_evolution_metrics(db_session, now)  # type: ignore[arg-type]
        assert result["trades"] == 1
        assert result["retorno_pct"] == pytest.approx((110000 - 100000) / 100000 * 100)
        assert Decimal(result["max_dd_pct"]) == pytest.approx(
            Decimal(str((100000 - 90000) / 100000 * 100)), abs=Decimal("0.01")
        )

    async def test_no_equity_data_returns_none_for_returns_and_dd(self, db_session: object) -> None:
        result = await monthly_evolution_metrics(db_session, datetime.now(UTC))  # type: ignore[arg-type]
        assert result["trades"] == 0
        assert result["retorno_pct"] is None
        assert result["max_dd_pct"] is None


class TestConfirmAdvanceIncludesMonthlyMetrics:
    async def test_metrics_dict_includes_trades_return_and_max_dd(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            UmsPhaseLog(
                ts=now - timedelta(days=100),
                phase=2,
                equity_at=Decimal("20000"),
                metrics={},
                ready_to_advance=False,
                signed_by=None,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await confirm_advance(
            db_session,
            GOOD_METRICS,
            CONFIG,
            "ivan",
            Decimal("30000"),
            now,  # type: ignore[arg-type]
        )
        assert "trades" in result.metrics
        assert "retorno_pct" in result.metrics
        assert "max_dd_pct" in result.metrics


class TestCheckAutomaticDowngradeIncludesMonthlyMetrics:
    async def test_metrics_dict_includes_trades_return_and_max_dd(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            UmsPhaseLog(
                ts=now - timedelta(days=10),
                phase=4,
                equity_at=Decimal("150000"),
                metrics={},
                ready_to_advance=False,
                signed_by="ivan",
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        await check_automatic_downgrade(db_session, redis, CONFIG, Decimal("20000"), now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        latest = await current_phase(db_session)  # type: ignore[arg-type]
        assert latest is not None
        assert "trades" in latest.metrics
        assert "retorno_pct" in latest.metrics
        assert "max_dd_pct" in latest.metrics
        await redis.aclose()
