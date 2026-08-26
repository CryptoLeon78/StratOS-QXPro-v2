"""PARTE 6.3: gate de 7 criterios (GO/HOLD/KILL, SIZING_CAP, PROVISIONAL) +
casos limite literales del seed (Estige PF32,75/9 trades -> HOLD; Sigma MR
95d/51 -> GO)."""

import json
from datetime import UTC, datetime

import fakeredis

from core.db.enums import PipelinePhase, Verdict
from core.state_machines.pipeline import apply_pipeline_gate, evaluate_pipeline_gate
from core.state_machines.types import PipelineGateConfig, PipelineGateMetrics
from tests.factories import AccountFactory, BotFactory

CONFIG = PipelineGateConfig()


def _metrics(
    profit_factor: float = 2.0,
    expectancy_r: float = 0.3,
    sharpe: float = 1.5,
    max_dd_pct: float = 10.0,
    oos_trades: int = 40,
    incubation_days: int = 70,
    trades_per_week: float = 3.0,
) -> PipelineGateMetrics:
    return PipelineGateMetrics(
        profit_factor=profit_factor,
        expectancy_r=expectancy_r,
        sharpe=sharpe,
        max_dd_pct=max_dd_pct,
        oos_trades=oos_trades,
        incubation_days=incubation_days,
        trades_per_week=trades_per_week,
    )


class TestGoVerdict:
    def test_sigma_mr_95_days_51_trades_all_criteria_pass_is_go(self) -> None:
        result = evaluate_pipeline_gate(
            _metrics(
                profit_factor=1.8,
                expectancy_r=0.2,
                sharpe=1.3,
                max_dd_pct=12.0,
                oos_trades=51,
                incubation_days=95,
                trades_per_week=4.0,
            ),
            CONFIG,
        )
        assert result.verdict == Verdict.GO.value
        assert result.gates_passed == 7
        assert result.gates_total == 7
        assert result.provisional is False
        assert result.verdict_reason is None


class TestHoldVerdict:
    def test_estige_pf3275_9_trades_insufficient_sample_is_hold_and_provisional(self) -> None:
        result = evaluate_pipeline_gate(
            _metrics(profit_factor=32.75, oos_trades=9, incubation_days=70),
            CONFIG,
        )
        assert result.verdict == Verdict.HOLD.value
        assert result.provisional is True
        assert result.gates_passed == 6

    def test_marginal_single_criterion_is_hold(self) -> None:
        # PF 1.48 vs umbral 1.5: falla por <10% -> marginal
        result = evaluate_pipeline_gate(_metrics(profit_factor=1.48), CONFIG)
        assert result.verdict == Verdict.HOLD.value
        assert result.gates_passed == 6

    def test_sizing_cap_breach_forces_hold_even_with_7_of_7(self) -> None:
        result = evaluate_pipeline_gate(
            _metrics(
                profit_factor=1.8,
                expectancy_r=0.2,
                sharpe=1.3,
                max_dd_pct=12.0,
                oos_trades=51,
                incubation_days=95,
                trades_per_week=4.0,
            ),
            CONFIG,
            sizing_cap_breach=True,
        )
        assert result.verdict == Verdict.HOLD.value
        assert result.verdict_reason == "SIZING_CAP"


class TestKillVerdict:
    def test_two_or_more_criteria_failing_is_kill(self) -> None:
        result = evaluate_pipeline_gate(
            _metrics(profit_factor=1.2, sharpe=0.5),  # pf y sharpe fallan
            CONFIG,
        )
        assert result.verdict == Verdict.KILL.value

    def test_maxdd_beyond_20_pct_is_kill_even_if_only_criterion_failing(self) -> None:
        result = evaluate_pipeline_gate(_metrics(max_dd_pct=21.0), CONFIG)
        assert result.verdict == Verdict.KILL.value

    def test_pf_below_11_is_kill_even_if_only_criterion_failing(self) -> None:
        result = evaluate_pipeline_gate(_metrics(profit_factor=1.05), CONFIG)
        assert result.verdict == Verdict.KILL.value

    def test_kill_takes_priority_over_sizing_cap(self) -> None:
        result = evaluate_pipeline_gate(
            _metrics(profit_factor=1.2, sharpe=0.5), CONFIG, sizing_cap_breach=True
        )
        assert result.verdict == Verdict.KILL.value


class TestApplyPipelineGatePersistence:
    async def test_updates_candidate_and_publishes_event(self, db_session: object) -> None:
        from sqlalchemy import select

        from core.db.models.decisions import DecisionLog
        from core.db.models.pipeline import PipelineCandidate

        redis = fakeredis.FakeAsyncRedis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("events:pipeline")
        await pubsub.get_message(timeout=1)

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=PipelinePhase.F4,
            entered_phase_at=datetime.now(UTC),
            incubation_days=70,
            oos_trades=40,
        )
        db_session.add(candidate)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        result = evaluate_pipeline_gate(_metrics(profit_factor=1.05), CONFIG)
        await apply_pipeline_gate(db_session, redis, candidate, result)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        refreshed = await db_session.get(PipelineCandidate, candidate.id)  # type: ignore[attr-defined]
        assert refreshed is not None
        assert refreshed.verdict == Verdict.KILL
        assert refreshed.evaluated_at is not None

        decision_log = (
            await db_session.execute(select(DecisionLog).where(DecisionLog.module == "pipeline"))  # type: ignore[attr-defined]
        ).scalar_one()
        assert decision_log.decision_type == "PIPELINE_GATE_EVALUATED"

        message = await pubsub.get_message(timeout=1)
        payload = json.loads(message["data"])
        assert payload["type"] == "pipeline.gate_evaluated"
        assert payload["verdict"] == "KILL"
        assert payload["candidate_id"] == candidate.id

        await pubsub.aclose()
        await redis.aclose()
