from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
import pytest
from sqlalchemy import select

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
