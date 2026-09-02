"""Gate de admisión a Incubadora: los dos criterios de descorrelación (backlog A18).

El tope por símbolo/timeframe y la correlación entre curvas miden cosas distintas y ninguno
sustituye al otro:

- **Estructural** — no ocho bots del mismo par y marco temporal. Aunque sus reglas difieran,
  comparten el mismo mercado y el mismo horizonte: el kill-switch los vería caer juntos.
- **Estadístico** — dos `AUDCAD/H4` con correlación 0,2 diversifican; dos con 0,9 no, aunque
  el tope estructural los deje pasar. Y al revés: dos instrumentos distintos con correlación
  0,95 tampoco diversifican, aunque ningún tope por símbolo los toque.

Un candidato de Análisis **no ha operado todavía**, así que su serie de PnL sale del backtest.
Eso hace que la correlación sea backtest-contra-real, no real-contra-real: se admite como
señal, pero el gate lo declara en vez de presentarla como equivalente.
"""

from __future__ import annotations

from core.services.incubator_admission import (
    AdmissionConfig,
    AdmissionDecision,
    IncubatorSlot,
    evaluate_admission,
)

CONFIG = AdmissionConfig(max_per_symbol_timeframe=2, max_concurrent=8, max_abs_correlation=0.7)


def _slot(bot_id: int, symbol: str, timeframe: str, pnl: list[float]) -> IncubatorSlot:
    return IncubatorSlot(bot_id=bot_id, symbol=symbol, timeframe=timeframe, pnl_series=pnl)


ALCISTA = [1.0, 2.0, -1.0, 3.0, 1.5, -0.5, 2.5, 1.0]
ESPEJO = [1.05, 2.1, -0.95, 3.1, 1.45, -0.55, 2.6, 1.05]  # casi identica
# Correlacion 0,00 con ALCISTA y -0,09 con la segunda ocupante: descorrelacion real,
# no una serie que simplemente parece distinta a ojo.
INDEPENDIENTE = [0.7, -1.0, -2.1, -0.5, -1.7, 0.0, -1.5, 1.3]


class TestStructuralCriterion:
    def test_admits_when_the_bucket_has_room(self) -> None:
        ocupados = [_slot(1, "AUDCAD", "H4", INDEPENDIENTE)]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is True

    def test_holds_when_the_symbol_timeframe_bucket_is_full(self) -> None:
        """Dos AUDCAD/H4 ya dentro y el tope es 2: el tercero espera aunque descorrele."""
        ocupados = [
            _slot(1, "AUDCAD", "H4", INDEPENDIENTE),
            _slot(2, "AUDCAD", "H4", [-1.0, 0.5, 1.0, -2.0, 3.0, 0.0, -1.5, 2.0]),
        ]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is False
        assert decision.reason == "SYMBOL_TIMEFRAME_CAP"

    def test_a_different_timeframe_is_a_different_bucket(self) -> None:
        ocupados = [
            _slot(1, "AUDCAD", "H4", INDEPENDIENTE),
            _slot(2, "AUDCAD", "H4", INDEPENDIENTE),
        ]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H1", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is True


class TestStatisticalCriterion:
    def test_holds_a_candidate_that_mirrors_an_occupant(self) -> None:
        """El caso que el tope estructural no ve: mismo bucket con hueco, curvas gemelas."""
        ocupados = [_slot(1, "AUDCAD", "H4", ESPEJO)]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is False
        assert decision.reason == "CORRELATED_WITH_OCCUPANT"
        assert decision.correlated_with == 1
        assert decision.max_abs_correlation is not None
        assert decision.max_abs_correlation > 0.9

    def test_holds_across_different_symbols_too(self) -> None:
        """Dos instrumentos distintos con curvas gemelas tampoco diversifican."""
        ocupados = [_slot(7, "EURUSD", "H1", ESPEJO)]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is False
        assert decision.reason == "CORRELATED_WITH_OCCUPANT"
        assert decision.correlated_with == 7

    def test_admits_an_independent_curve_in_the_same_bucket(self) -> None:
        ocupados = [_slot(1, "AUDCAD", "H4", INDEPENDIENTE)]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is True
        assert decision.max_abs_correlation is not None

    def test_an_inverse_curve_is_as_redundant_as_a_parallel_one(self) -> None:
        """Correlación -0,95 no es diversificación: es la misma apuesta al reves, y el
        kill-switch la ve caer cuando la otra sube. Se mide en valor absoluto."""
        inversa = [-value for value in ESPEJO]
        ocupados = [_slot(3, "AUDCAD", "H4", inversa)]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is False
        assert decision.reason == "CORRELATED_WITH_OCCUPANT"


class TestCapacityAndAbsence:
    def test_holds_when_the_incubator_is_full(self) -> None:
        ocupados = [_slot(i, f"SYM{i}", "H1", INDEPENDIENTE) for i in range(8)]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is False
        assert decision.reason == "INCUBATOR_FULL"

    def test_an_empty_incubator_admits_the_first_candidate(self) -> None:
        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=[], config=CONFIG
        )

        assert decision.admitted is True
        assert decision.max_abs_correlation is None

    def test_a_candidate_without_a_series_is_held_not_admitted_blind(self) -> None:
        """Fail-closed: sin serie no se puede medir descorrelación, y admitir a ciegas
        rompería el criterio que este gate existe para aplicar."""
        ocupados = [_slot(1, "AUDCAD", "H4", INDEPENDIENTE)]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=[], occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is False
        assert decision.reason == "NO_SERIES_FOR_CORRELATION"

    def test_an_occupant_without_a_series_does_not_silently_pass(self) -> None:
        """Un ocupante sin serie no puede compararse: se declara, no se ignora."""
        ocupados = [_slot(1, "AUDCAD", "H4", [])]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.admitted is False
        assert decision.reason == "OCCUPANT_WITHOUT_SERIES"
        assert decision.correlated_with == 1

    def test_the_structural_criterion_is_checked_before_the_statistical_one(self) -> None:
        """Si el bucket esta lleno da igual lo que diga la correlacion: el motivo que se
        reporta es el que de verdad bloquea."""
        ocupados = [
            _slot(1, "AUDCAD", "H4", INDEPENDIENTE),
            _slot(2, "AUDCAD", "H4", INDEPENDIENTE),
        ]

        decision = evaluate_admission(
            symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=ocupados, config=CONFIG
        )

        assert decision.reason == "SYMBOL_TIMEFRAME_CAP"


def test_the_decision_is_serialisable_for_the_append_only_record() -> None:
    decision = evaluate_admission(
        symbol="AUDCAD", timeframe="H4", pnl_series=ALCISTA, occupied=[], config=CONFIG
    )

    assert isinstance(decision, AdmissionDecision)
    assert decision.as_evidence()["admitted"] is True
    assert decision.as_evidence()["config"]["max_abs_correlation"] == 0.7
