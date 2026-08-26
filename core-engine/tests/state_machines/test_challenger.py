"""PARTE 6.3: rotacion champion/challenger (5 criterios, ejemplo real Helios
Sharpe x1,22 p=0,03) + cementerio (autopsia obligatoria, property-based sin
retorno) + overstay (>6 meses)."""

import json

import fakeredis
from hypothesis import given, settings
from hypothesis import strategies as st

from core.db.enums import AlertLevel, CemeteryCause, PipelinePhase
from core.state_machines.challenger import (
    apply_cemetery_archival,
    apply_challenger_rotation,
    apply_overstay_alert,
    evaluate_cemetery_reactivation,
    evaluate_challenger,
    evaluate_overstay,
)
from core.state_machines.types import ChallengerConfig, ChallengerMetrics
from tests.factories import AccountFactory, BotFactory

CONFIG = ChallengerConfig()


def _metrics(
    sharpe: float = 1.0,
    p_value: float = 0.5,
    correlation_with_block: float = 0.3,
    max_dd_pct: float = 10.0,
    expectancy_r: float = 0.2,
) -> ChallengerMetrics:
    return ChallengerMetrics(
        sharpe=sharpe,
        p_value=p_value,
        correlation_with_block=correlation_with_block,
        max_dd_pct=max_dd_pct,
        expectancy_r=expectancy_r,
    )


class TestEvaluateChallenger:
    def test_helios_real_example_passes_all_5_criteria(self) -> None:
        champion = _metrics(
            sharpe=1.0, correlation_with_block=0.31, max_dd_pct=12.0, expectancy_r=0.15
        )
        challenger = _metrics(
            sharpe=1.22,
            p_value=0.03,
            correlation_with_block=0.31,
            max_dd_pct=12.0,
            expectancy_r=0.15,
        )
        result = evaluate_challenger(challenger, champion, CONFIG)
        assert result.passed is True
        assert all(result.criteria.values())

    def test_sharpe_below_122x_champion_fails(self) -> None:
        champion = _metrics(sharpe=1.0)
        challenger = _metrics(sharpe=1.1, p_value=0.03)
        result = evaluate_challenger(challenger, champion, CONFIG)
        assert result.passed is False
        assert result.criteria["sharpe"] is False

    def test_p_value_not_significant_fails(self) -> None:
        champion = _metrics(sharpe=1.0)
        challenger = _metrics(sharpe=1.5, p_value=0.10)
        result = evaluate_challenger(challenger, champion, CONFIG)
        assert result.passed is False
        assert result.criteria["p_value"] is False

    def test_higher_correlation_with_block_fails(self) -> None:
        champion = _metrics(correlation_with_block=0.2)
        challenger = _metrics(sharpe=1.5, p_value=0.01, correlation_with_block=0.5)
        result = evaluate_challenger(challenger, champion, CONFIG)
        assert result.criteria["correlation_not_higher"] is False

    def test_higher_maxdd_fails(self) -> None:
        champion = _metrics(max_dd_pct=10.0)
        challenger = _metrics(sharpe=1.5, p_value=0.01, max_dd_pct=15.0)
        result = evaluate_challenger(challenger, champion, CONFIG)
        assert result.criteria["maxdd_not_higher"] is False

    def test_lower_expectancy_fails(self) -> None:
        champion = _metrics(expectancy_r=0.3)
        challenger = _metrics(sharpe=1.5, p_value=0.01, expectancy_r=0.1)
        result = evaluate_challenger(challenger, champion, CONFIG)
        assert result.criteria["expectancy_not_lower"] is False


class TestOverstay:
    def test_within_6_months_is_not_overstay(self) -> None:
        assert evaluate_overstay(5, CONFIG) is False

    def test_beyond_6_months_is_overstay(self) -> None:
        assert evaluate_overstay(7, CONFIG) is True


class TestCemeteryReactivationNeverAllowed:
    def test_always_rejects(self) -> None:
        result = evaluate_cemetery_reactivation(bot_id=1, config=CONFIG)
        assert result.allowed is False
        assert result.reason == CONFIG.cemetery_banner

    @given(
        bot_id=st.integers(min_value=1, max_value=10_000),
        signed_by=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
        justification=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
    )
    @settings(max_examples=200)
    def test_property_never_allowed_regardless_of_input(
        self, bot_id: int, signed_by: str | None, justification: str | None
    ) -> None:
        result = evaluate_cemetery_reactivation(
            bot_id=bot_id, config=CONFIG, signed_by=signed_by, justification=justification
        )
        assert result.allowed is False


class TestApplyCemeteryArchival:
    async def test_empty_autopsy_text_raises_before_touching_db(self, db_session: object) -> None:
        import pytest

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        with pytest.raises(ValueError, match="autopsy_text"):
            await apply_cemetery_archival(
                db_session,  # type: ignore[arg-type]
                redis,
                bot,
                CemeteryCause.ALPHA_DECAY,
                autopsy_text="   ",
                lesson="valida",
            )
        await redis.aclose()

    async def test_empty_lesson_raises_before_touching_db(self, db_session: object) -> None:
        import pytest

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        with pytest.raises(ValueError, match="lesson"):
            await apply_cemetery_archival(
                db_session,  # type: ignore[arg-type]
                redis,
                bot,
                CemeteryCause.ALPHA_DECAY,
                autopsy_text="valida",
                lesson="",
            )
        await redis.aclose()

    async def test_archives_bot_and_publishes_event(self, db_session: object) -> None:
        from sqlalchemy import select

        from core.db.models.pipeline import CemeteryEntry

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id, slot="trend-eurusd-h4")
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("events:pipeline")
        await pubsub.get_message(timeout=1)

        await apply_cemetery_archival(
            db_session,  # type: ignore[arg-type]
            redis,
            bot,
            CemeteryCause.OVERFITTING,
            autopsy_text="Backtest sobreajustado a 2019-2021, no replicable en forward.",
            lesson="Exigir OOS mas largo antes de F4.",
        )
        await db_session.commit()  # type: ignore[attr-defined]

        entry = (
            await db_session.execute(select(CemeteryEntry).where(CemeteryEntry.bot_id == bot.id))  # type: ignore[attr-defined]
        ).scalar_one()
        assert entry.cause == CemeteryCause.OVERFITTING
        assert entry.reactivation_blocked is True

        assert bot.pipeline_phase == PipelinePhase.CEMENTERIO
        assert bot.slot is None

        message = await pubsub.get_message(timeout=1)
        payload = json.loads(message["data"])
        assert payload["type"] == "cemetery.archived"
        assert payload["bot_id"] == bot.id

        await pubsub.aclose()
        await redis.aclose()


class TestApplyChallengerRotation:
    async def test_challenger_wins_champion_archived_and_slot_transferred(
        self, db_session: object
    ) -> None:
        from sqlalchemy import select

        from core.db.models.pipeline import CemeteryEntry, ChallengerEvaluation

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        champion = BotFactory(account_id=account.id, slot="trend-eurusd-h4")
        challenger = BotFactory(account_id=account.id, slot=None)
        db_session.add_all([champion, challenger])  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        champion_metrics = _metrics(sharpe=1.0, correlation_with_block=0.31)
        challenger_metrics = _metrics(sharpe=1.22, p_value=0.03, correlation_with_block=0.31)
        evaluation = evaluate_challenger(challenger_metrics, champion_metrics, CONFIG)
        assert evaluation.passed is True

        await apply_challenger_rotation(
            db_session,  # type: ignore[arg-type]
            redis,
            challenger,
            champion,
            slot="trend-eurusd-h4",
            evaluation=evaluation,
            p_value=0.03,
        )
        await db_session.commit()  # type: ignore[attr-defined]

        cemetery_entry = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(CemeteryEntry).where(CemeteryEntry.bot_id == champion.id)
            )
        ).scalar_one()
        assert cemetery_entry.cause == CemeteryCause.OUTPERFORMED_BY_CHALLENGER

        challenger_eval = (
            await db_session.execute(select(ChallengerEvaluation))  # type: ignore[attr-defined]
        ).scalar_one()
        assert challenger_eval.passed is True
        assert challenger_eval.slot == "trend-eurusd-h4"

        assert challenger.slot == "trend-eurusd-h4"
        assert champion.slot is None

        await redis.aclose()

    async def test_challenger_loses_no_rotation_happens(self, db_session: object) -> None:
        from sqlalchemy import select

        from core.db.models.pipeline import CemeteryEntry, ChallengerEvaluation

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        champion = BotFactory(account_id=account.id, slot="trend-eurusd-h4")
        challenger = BotFactory(account_id=account.id, slot=None)
        db_session.add_all([champion, challenger])  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        champion_metrics = _metrics(sharpe=2.0)
        challenger_metrics = _metrics(sharpe=1.0, p_value=0.5)
        evaluation = evaluate_challenger(challenger_metrics, champion_metrics, CONFIG)
        assert evaluation.passed is False

        await apply_challenger_rotation(
            db_session,  # type: ignore[arg-type]
            redis,
            challenger,
            champion,
            slot="trend-eurusd-h4",
            evaluation=evaluation,
            p_value=0.5,
        )
        await db_session.commit()  # type: ignore[attr-defined]

        assert (
            await db_session.execute(select(CemeteryEntry))  # type: ignore[attr-defined]
        ).scalar_one_or_none() is None
        challenger_eval = (
            await db_session.execute(select(ChallengerEvaluation))  # type: ignore[attr-defined]
        ).scalar_one()
        assert challenger_eval.passed is False
        assert champion.slot == "trend-eurusd-h4"
        assert challenger.slot is None

        await redis.aclose()


class TestApplyOverstayAlert:
    async def test_creates_alert_and_publishes_event(self, db_session: object) -> None:
        from sqlalchemy import select

        from core.db.models.decisions import Alert

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("events:pipeline")
        await pubsub.get_message(timeout=1)

        await apply_overstay_alert(db_session, redis, bot, CONFIG)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alert = (
            await db_session.execute(select(Alert).where(Alert.module == "challenger"))  # type: ignore[attr-defined]
        ).scalar_one()
        assert alert.level == AlertLevel.SUAVE
        assert alert.action_required == CONFIG.instruction_overstay

        message = await pubsub.get_message(timeout=1)
        payload = json.loads(message["data"])
        assert payload["type"] == "challenger.overstay"
        assert payload["bot_id"] == bot.id

        await pubsub.aclose()
        await redis.aclose()
