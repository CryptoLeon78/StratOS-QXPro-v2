"""PARTE 6.2: kill-switch de portfolio (4 niveles) + desescalado firmado con
histeresis + property-based (nunca desescala sin firma)."""

import json
from decimal import Decimal

import fakeredis
from hypothesis import given, settings
from hypothesis import strategies as st

from core.db.enums import AlertLevel
from core.state_machines.killswitch import (
    apply_killswitch_transition,
    evaluate_killswitch_deescalation,
    evaluate_killswitch_escalation,
)
from core.state_machines.types import KillSwitchConfig

CONFIG = KillSwitchConfig()


class TestEscalation:
    def test_below_l1_stays_at_zero(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("5"), current_level=0, config=CONFIG)
        assert result.changed is False
        assert result.to_state == "0"

    def test_reaches_l1_notifies_without_confirmation(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("8"), current_level=0, config=CONFIG)
        assert result.changed is True
        assert result.to_state == "1"
        assert result.instruction_text == CONFIG.instruction_l1
        assert result.severity == AlertLevel.INFO
        assert result.requires_confirmation is False

    def test_reaches_l2_requires_confirmation(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("12"), current_level=1, config=CONFIG)
        assert result.changed is True
        assert result.to_state == "2"
        assert result.instruction_text == CONFIG.instruction_l2
        assert result.severity == AlertLevel.CRITICA
        assert result.requires_confirmation is True

    def test_reaches_l3(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("15"), current_level=2, config=CONFIG)
        assert result.to_state == "3"
        assert result.instruction_text == CONFIG.instruction_l3

    def test_reaches_l4(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("20"), current_level=3, config=CONFIG)
        assert result.to_state == "4"
        assert result.instruction_text == CONFIG.instruction_l4

    def test_sudden_jump_skips_directly_to_l4(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("25"), current_level=0, config=CONFIG)
        assert result.to_state == "4"

    def test_already_at_target_level_does_not_retrigger(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("13"), current_level=2, config=CONFIG)
        assert result.changed is False
        assert result.to_state == "2"

    def test_dd_recovery_never_auto_deescalates(self) -> None:
        result = evaluate_killswitch_escalation(Decimal("9"), current_level=3, config=CONFIG)
        assert result.changed is False
        assert result.to_state == "3"


class TestDeescalation:
    def test_without_signature_never_deescalates(self) -> None:
        result = evaluate_killswitch_deescalation(
            Decimal("5"), current_level=2, config=CONFIG, signed_by=None
        )
        assert result.changed is False
        assert result.to_state == "2"

    def test_above_hysteresis_band_does_not_deescalate_even_with_signature(self) -> None:
        # L2 umbral=12, histeresis=2 -> hace falta DD<10 para desescalar
        result = evaluate_killswitch_deescalation(
            Decimal("11"), current_level=2, config=CONFIG, signed_by="operator@example.com"
        )
        assert result.changed is False
        assert result.to_state == "2"

    def test_below_hysteresis_band_with_signature_deescalates(self) -> None:
        result = evaluate_killswitch_deescalation(
            Decimal("9"), current_level=2, config=CONFIG, signed_by="operator@example.com"
        )
        assert result.changed is True
        assert result.to_state == "1"
        assert result.requires_confirmation is False

    def test_deescalates_directly_to_zero_when_dd_fully_recovered(self) -> None:
        result = evaluate_killswitch_deescalation(
            Decimal("1"), current_level=1, config=CONFIG, signed_by="operator@example.com"
        )
        assert result.changed is True
        assert result.to_state == "0"

    def test_at_level_zero_is_a_noop(self) -> None:
        result = evaluate_killswitch_deescalation(
            Decimal("0"), current_level=0, config=CONFIG, signed_by="operator@example.com"
        )
        assert result.changed is False


class TestNeverDeescalatesWithoutSignatureProperty:
    @given(
        portfolio_dd_pct=st.decimals(min_value="0", max_value="30", places=2, allow_nan=False),
        current_level=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=200)
    def test_property(self, portfolio_dd_pct: Decimal, current_level: int) -> None:
        result = evaluate_killswitch_deescalation(
            portfolio_dd_pct, current_level=current_level, config=CONFIG, signed_by=None
        )
        assert result.changed is False
        assert result.to_state == str(current_level)


class TestApplyKillswitchTransitionPersistence:
    async def test_persists_event_decisionlog_and_publishes_event(self, db_session: object) -> None:
        from sqlalchemy import select

        from core.db.models.decisions import DecisionLog, KillSwitchEvent

        redis = fakeredis.FakeAsyncRedis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("events:killswitch")
        await pubsub.get_message(timeout=1)

        result = evaluate_killswitch_escalation(Decimal("12"), current_level=1, config=CONFIG)
        await apply_killswitch_transition(db_session, redis, result)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        event = (
            await db_session.execute(select(KillSwitchEvent))  # type: ignore[attr-defined]
        ).scalar_one()
        assert event.level == 2
        assert event.portfolio_dd_pct == Decimal("12")
        assert event.instruction_text == CONFIG.instruction_l2

        decision_log = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(DecisionLog).where(DecisionLog.module == "killswitch")
            )
        ).scalar_one()
        assert decision_log.decision_type == "KILLSWITCH_ESCALATION"

        message = await pubsub.get_message(timeout=1)
        payload = json.loads(message["data"])
        assert payload["type"] == "killswitch.transition"
        assert payload["from"] == "1"
        assert payload["to"] == "2"
        assert payload["requires_confirmation"] is True

        await pubsub.aclose()
        await redis.aclose()

    async def test_unchanged_result_is_a_noop(self, db_session: object) -> None:
        from sqlalchemy import select

        from core.db.models.decisions import KillSwitchEvent

        redis = fakeredis.FakeAsyncRedis()
        result = evaluate_killswitch_escalation(Decimal("5"), current_level=0, config=CONFIG)
        assert result.changed is False
        await apply_killswitch_transition(db_session, redis, result)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        rows = (
            (await db_session.execute(select(KillSwitchEvent)))  # type: ignore[attr-defined]
            .scalars()
            .all()
        )
        assert rows == []
        await redis.aclose()
