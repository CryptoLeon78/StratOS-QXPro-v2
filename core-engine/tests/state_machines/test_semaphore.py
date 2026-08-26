"""PARTE 6.1: semaforo por bot VERDE/AMARILLO/NARANJA. Todas las
transiciones de la tabla + property-based (ninguna transicion invalida
alcanzable) + demo obligatoria de PARTE 12 (Poseidon, PF 1,18 vs 1,94)."""

import json
from decimal import Decimal

import fakeredis
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.db.enums import AlertLevel, SemaphoreState
from core.state_machines.semaphore import apply_semaphore_transition, evaluate_semaphore_transition
from core.state_machines.types import SemaphoreConfig, SemaphoreMetrics
from tests.factories import AccountFactory, BotFactory

MAGIC = 118685
CONFIG = SemaphoreConfig()


def _metrics(
    pf_rolling: float = 1.9,
    pf_baseline: float = 1.9,
    exp_rolling: float = 0.2,
    exp_baseline: float = 0.2,
    loss_streak: int = 2,
    loss_streak_p99_baseline: int = 6,
    page_hinkley_triggered: bool = False,
    dd_bot_pct: str = "1.0",
    dd_contract_pct: str = "3.9",
    pf_virtual: float | None = None,
    exp_virtual: float | None = None,
) -> SemaphoreMetrics:
    return SemaphoreMetrics(
        pf_rolling=pf_rolling,
        pf_baseline=pf_baseline,
        exp_rolling=exp_rolling,
        exp_baseline=exp_baseline,
        loss_streak=loss_streak,
        loss_streak_p99_baseline=loss_streak_p99_baseline,
        page_hinkley_triggered=page_hinkley_triggered,
        dd_bot_pct=Decimal(dd_bot_pct),
        dd_contract_pct=Decimal(dd_contract_pct),
        pf_virtual=pf_virtual,
        exp_virtual=exp_virtual,
    )


class TestVerdeToAmarillo:
    def test_healthy_bot_stays_verde(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.VERDE, _metrics(), CONFIG, magic_number=MAGIC
        )
        assert result.changed is False
        assert result.to_state == "VERDE"

    def test_pf_below_warn_triggers_amarillo(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.VERDE,
            _metrics(pf_rolling=1.0, pf_baseline=1.94),  # 1.0/1.94=0.515 < 0.75
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.changed is True
        assert result.to_state == "AMARILLO"
        assert result.instruction_text == CONFIG.instruction_amarillo
        assert result.new_sizing_pct == Decimal("50")

    def test_exp_below_warn_triggers_amarillo(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.VERDE,
            _metrics(exp_rolling=0.05, exp_baseline=0.2),  # 0.25 < 0.60
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.to_state == "AMARILLO"

    def test_loss_streak_beyond_p99_triggers_amarillo(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.VERDE,
            _metrics(loss_streak=8, loss_streak_p99_baseline=6),
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.to_state == "AMARILLO"

    def test_page_hinkley_triggers_amarillo(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.VERDE,
            _metrics(page_hinkley_triggered=True),
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.to_state == "AMARILLO"


class TestAmarilloToVerde:
    def test_recovers_after_recovery_days(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.AMARILLO,
            _metrics(pf_rolling=1.8, pf_baseline=1.9, exp_rolling=0.18, exp_baseline=0.2),
            CONFIG,
            magic_number=MAGIC,
            days_meeting_recovery_condition=10,
        )
        assert result.changed is True
        assert result.to_state == "VERDE"
        assert result.new_sizing_pct == Decimal("100")
        assert result.severity == AlertLevel.INFO

    def test_not_yet_sustained_stays_amarillo(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.AMARILLO,
            _metrics(pf_rolling=1.8, pf_baseline=1.9, exp_rolling=0.18, exp_baseline=0.2),
            CONFIG,
            magic_number=MAGIC,
            days_meeting_recovery_condition=3,
        )
        assert result.changed is False
        assert result.to_state == "AMARILLO"


class TestAmarilloToNaranja:
    def test_pf_below_orange_triggers_naranja(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.AMARILLO,
            _metrics(pf_rolling=1.0, pf_baseline=1.94),  # 0.515 < 0.60
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.changed is True
        assert result.to_state == "NARANJA"
        assert result.instruction_text == CONFIG.instruction_naranja_template.format(magic=MAGIC)
        assert result.severity == AlertLevel.CRITICA
        assert result.requires_confirmation is True

    def test_15_days_without_recovery_triggers_naranja(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.AMARILLO,
            _metrics(pf_rolling=1.18, pf_baseline=1.94),  # 0.608, no dispara solo por PF
            CONFIG,
            magic_number=MAGIC,
            days_in_amarillo=15,
        )
        assert result.to_state == "NARANJA"

    def test_dd_bot_beyond_80_pct_contract_triggers_naranja(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.AMARILLO,
            _metrics(dd_bot_pct="3.5", dd_contract_pct="3.9"),  # 3.5 > 0.8*3.9=3.12
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.to_state == "NARANJA"


class TestContractBreachFromAnyState:
    @pytest.mark.parametrize("state", [SemaphoreState.VERDE, SemaphoreState.AMARILLO])
    def test_dd_bot_exceeds_contract_triggers_naranja(self, state: SemaphoreState) -> None:
        result = evaluate_semaphore_transition(
            state,
            _metrics(dd_bot_pct="4.5", dd_contract_pct="3.9"),
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.changed is True
        assert result.to_state == "NARANJA"
        assert result.decision_type == "CONTRACT_BREACH"

    def test_already_naranja_does_not_retrigger(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.NARANJA,
            _metrics(dd_bot_pct="4.5", dd_contract_pct="3.9"),
            CONFIG,
            magic_number=MAGIC,
        )
        assert result.changed is False
        assert result.to_state == "NARANJA"


class TestNaranjaToVerde:
    def test_reactivates_with_signature_and_clean_virtual_trades(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.NARANJA,
            _metrics(pf_virtual=1.8, exp_virtual=0.1, pf_baseline=1.9),
            CONFIG,
            magic_number=MAGIC,
            virtual_trades_clean=30,
            signed_by="operator@example.com",
        )
        assert result.changed is True
        assert result.to_state == "VERDE"

    def test_without_signature_never_reactivates(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.NARANJA,
            _metrics(pf_virtual=1.8, exp_virtual=0.1, pf_baseline=1.9),
            CONFIG,
            magic_number=MAGIC,
            virtual_trades_clean=30,
            signed_by=None,
        )
        assert result.changed is False
        assert result.to_state == "NARANJA"

    def test_not_enough_virtual_trades_stays_naranja(self) -> None:
        result = evaluate_semaphore_transition(
            SemaphoreState.NARANJA,
            _metrics(pf_virtual=1.8, exp_virtual=0.1, pf_baseline=1.9),
            CONFIG,
            magic_number=MAGIC,
            virtual_trades_clean=10,
            signed_by="operator@example.com",
        )
        assert result.changed is False


class TestDemoPoseidon:
    def test_poseidon_pf118_vs_194_15_dias_amarillo_produces_literal_naranja_instruction(
        self,
    ) -> None:
        """PARTE 12 (demo obligatoria de G3) + PARTE 1: Poseidon Trend GER40,
        magic 118685, PF rodante 1,18 vs baseline 1,94, 12-15 dias en
        AMARILLO/NARANJA sin recuperar."""
        result = evaluate_semaphore_transition(
            SemaphoreState.AMARILLO,
            _metrics(pf_rolling=1.18, pf_baseline=1.94),
            CONFIG,
            magic_number=118685,
            days_in_amarillo=15,
        )
        assert result.to_state == "NARANJA"
        assert result.instruction_text == (
            "En el EA magic 118685: desactivar apertura de nuevas posiciones "
            "(modo paper) y dejar cerrar las existentes por sus reglas."
        )


class TestNoInvalidTransitionReachable:
    @given(
        state=st.sampled_from(list(SemaphoreState)),
        pf_rolling=st.floats(min_value=0.01, max_value=5, allow_nan=False),
        pf_baseline=st.floats(min_value=0.01, max_value=5, allow_nan=False),
        exp_rolling=st.floats(min_value=-1, max_value=1, allow_nan=False),
        exp_baseline=st.floats(min_value=0.01, max_value=1, allow_nan=False),
        loss_streak=st.integers(min_value=0, max_value=30),
        dd_bot_pct=st.decimals(min_value="0", max_value="30", places=2, allow_nan=False),
        dd_contract_pct=st.decimals(min_value="0.1", max_value="30", places=2, allow_nan=False),
        days_in_amarillo=st.integers(min_value=0, max_value=60),
        days_recovery=st.integers(min_value=0, max_value=60),
        virtual_trades=st.integers(min_value=0, max_value=60),
        signed=st.booleans(),
    )
    @settings(max_examples=200)
    def test_property_only_documented_transitions_happen(
        self,
        state: SemaphoreState,
        pf_rolling: float,
        pf_baseline: float,
        exp_rolling: float,
        exp_baseline: float,
        loss_streak: int,
        dd_bot_pct: Decimal,
        dd_contract_pct: Decimal,
        days_in_amarillo: int,
        days_recovery: int,
        virtual_trades: int,
        signed: bool,
    ) -> None:
        metrics = _metrics(
            pf_rolling=pf_rolling,
            pf_baseline=pf_baseline,
            exp_rolling=exp_rolling,
            exp_baseline=exp_baseline,
            loss_streak=loss_streak,
            dd_bot_pct=str(dd_bot_pct),
            dd_contract_pct=str(dd_contract_pct),
            pf_virtual=pf_rolling,
            exp_virtual=exp_rolling,
        )
        result = evaluate_semaphore_transition(
            state,
            metrics,
            CONFIG,
            magic_number=MAGIC,
            days_in_amarillo=days_in_amarillo,
            days_meeting_recovery_condition=days_recovery,
            virtual_trades_clean=virtual_trades,
            signed_by="op" if signed else None,
        )
        assert result.to_state in {"VERDE", "AMARILLO", "NARANJA"}
        if state == SemaphoreState.NARANJA:
            assert result.to_state in {"NARANJA", "VERDE"}  # nunca NARANJA->AMARILLO directo
        if state == SemaphoreState.VERDE:
            assert result.to_state in {"VERDE", "AMARILLO", "NARANJA"}
        if state == SemaphoreState.AMARILLO:
            assert result.to_state in {"AMARILLO", "VERDE", "NARANJA"}


class TestApplySemaphoreTransitionPersistence:
    async def test_persists_transition_decisionlog_and_publishes_event(
        self, db_session: object
    ) -> None:
        from sqlalchemy import select

        from core.db.models.accounts import Bot
        from core.db.models.decisions import Decision, DecisionLog, SemaphoreTransition

        redis = fakeredis.FakeAsyncRedis()
        pubsub = redis.pubsub()
        await pubsub.subscribe("events:semaphore")
        await pubsub.get_message(timeout=1)

        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.VERDE)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        result = evaluate_semaphore_transition(
            SemaphoreState.VERDE,
            _metrics(pf_rolling=1.0, pf_baseline=1.94),
            CONFIG,
            magic_number=bot.magic_number,
        )
        await apply_semaphore_transition(db_session, redis, bot, result)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        transition = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(SemaphoreTransition).where(SemaphoreTransition.bot_id == bot.id)
            )
        ).scalar_one()
        assert transition.from_state == SemaphoreState.VERDE
        assert transition.to_state == SemaphoreState.AMARILLO

        decision_log = (
            await db_session.execute(select(DecisionLog).where(DecisionLog.module == "semaphore"))  # type: ignore[attr-defined]
        ).scalar_one()
        assert decision_log.prev_hash == "0" * 64

        decision = (
            await db_session.execute(select(Decision).where(Decision.module == "semaphore"))  # type: ignore[attr-defined]
        ).scalar_one()
        assert decision.instruction_text == CONFIG.instruction_amarillo

        refreshed_bot = await db_session.get(Bot, bot.id)  # type: ignore[attr-defined]
        assert refreshed_bot is not None
        assert refreshed_bot.semaphore_state == SemaphoreState.AMARILLO
        assert refreshed_bot.sizing_current_pct == Decimal("50.00")

        message = await pubsub.get_message(timeout=1)
        payload = json.loads(message["data"])
        assert payload["type"] == "semaphore.transition"
        assert payload["bot_id"] == bot.id
        assert payload["magic_number"] == bot.magic_number
        assert payload["from"] == "VERDE"
        assert payload["to"] == "AMARILLO"
        assert payload["requires_confirmation"] is True

        await pubsub.aclose()
        await redis.aclose()

    async def test_unchanged_result_is_a_noop(self, db_session: object) -> None:
        from sqlalchemy import select

        from core.db.models.decisions import SemaphoreTransition

        redis = fakeredis.FakeAsyncRedis()
        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.VERDE)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        result = evaluate_semaphore_transition(
            SemaphoreState.VERDE, _metrics(), CONFIG, magic_number=bot.magic_number
        )
        assert result.changed is False
        await apply_semaphore_transition(db_session, redis, bot, result)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        rows = (
            (
                await db_session.execute(  # type: ignore[attr-defined]
                    select(SemaphoreTransition).where(SemaphoreTransition.bot_id == bot.id)
                )
            )
            .scalars()
            .all()
        )
        assert rows == []
        await redis.aclose()
