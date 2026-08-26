"""PARTE 8: audit_discrepancy, counterfactual_impulse, sustainable_withdrawal.
Pie de PARTE 8: nominal, division por cero, un elemento, extremos."""

from decimal import Decimal

import pytest

from core.db.enums import ImpulseAction
from core.formulas.audit import audit_discrepancy, counterfactual_impulse, sustainable_withdrawal
from core.formulas.types import ImpulseSnapshot, TradeLike, WithdrawalConfig


class TestAuditDiscrepancy:
    def test_nominal_matches_real_seed_zero_discrepancy(self) -> None:
        # PARTE 1: 30.000,00 + 147.616,18 = 177.616,18, descuadre 0,00 (0,00%)
        d = audit_discrepancy(
            initial=Decimal("30000.00"),
            flows=Decimal("147616.18"),
            final=Decimal("177616.18"),
        )
        assert d == Decimal("0")

    def test_final_zero_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            audit_discrepancy(initial=Decimal("100"), flows=Decimal("0"), final=Decimal("0"))

    def test_mismatch_gives_positive_discrepancy(self) -> None:
        d = audit_discrepancy(
            initial=Decimal("30000.00"),
            flows=Decimal("147616.18"),
            final=Decimal("177616.20"),
        )
        assert d > Decimal("0")

    def test_extreme_total_mismatch(self) -> None:
        d = audit_discrepancy(initial=Decimal("0"), flows=Decimal("0"), final=Decimal("100"))
        assert d == Decimal("1")


class TestCounterfactualImpulse:
    def _trade(self, profit: str) -> TradeLike:
        return TradeLike(profit=Decimal(profit), commission=Decimal("0"), swap=Decimal("0"))

    def test_close_position_avoided_loss(self) -> None:
        trades = [self._trade("-50"), self._trade("-30")]
        avoided = counterfactual_impulse(
            trades, ImpulseAction.CLOSE_POSITION, ImpulseSnapshot(sizing_multiplier=Decimal("1"))
        )
        assert avoided == Decimal("-80")

    def test_close_position_avoided_gain_is_negative(self) -> None:
        trades = [self._trade("50")]
        avoided = counterfactual_impulse(
            trades, ImpulseAction.CLOSE_POSITION, ImpulseSnapshot(sizing_multiplier=Decimal("1"))
        )
        assert avoided == Decimal("50")

    def test_decrease_risk_halves_simulated(self) -> None:
        trades = [self._trade("100")]
        avoided = counterfactual_impulse(
            trades,
            ImpulseAction.DECREASE_RISK,
            ImpulseSnapshot(sizing_multiplier=Decimal("0.5")),
        )
        assert avoided == Decimal("50")

    def test_other_action_is_zero(self) -> None:
        trades = [self._trade("100"), self._trade("-40")]
        avoided = counterfactual_impulse(
            trades, ImpulseAction.OTHER, ImpulseSnapshot(sizing_multiplier=Decimal("1"))
        )
        assert avoided == Decimal("0")

    def test_empty_trades_is_zero(self) -> None:
        avoided = counterfactual_impulse(
            [], ImpulseAction.CLOSE_POSITION, ImpulseSnapshot(sizing_multiplier=Decimal("1"))
        )
        assert avoided == Decimal("0")

    def test_includes_commission_and_swap(self) -> None:
        trade = TradeLike(profit=Decimal("100"), commission=Decimal("-5"), swap=Decimal("-2"))
        avoided = counterfactual_impulse(
            [trade], ImpulseAction.CLOSE_POSITION, ImpulseSnapshot(sizing_multiplier=Decimal("1"))
        )
        assert avoided == Decimal("93")


class TestSustainableWithdrawal:
    def test_nominal(self) -> None:
        config = WithdrawalConfig(safety_margin=Decimal("0.5"), max_dd_gate_pct=Decimal("10"))
        w = sustainable_withdrawal(
            avg_monthly_return=0.0269,
            max_dd=Decimal("4.76"),
            equity=Decimal("179642.70"),
            config=config,
        )
        assert w > Decimal("0")

    def test_max_dd_beyond_gate_is_zero(self) -> None:
        config = WithdrawalConfig(safety_margin=Decimal("0.5"), max_dd_gate_pct=Decimal("10"))
        w = sustainable_withdrawal(
            avg_monthly_return=0.03, max_dd=Decimal("15"), equity=Decimal("100000"), config=config
        )
        assert w == Decimal("0")

    def test_equity_zero_is_zero(self) -> None:
        config = WithdrawalConfig(safety_margin=Decimal("0.5"), max_dd_gate_pct=Decimal("10"))
        w = sustainable_withdrawal(
            avg_monthly_return=0.03, max_dd=Decimal("2"), equity=Decimal("0"), config=config
        )
        assert w == Decimal("0")

    def test_negative_return_clamped_to_zero(self) -> None:
        config = WithdrawalConfig(safety_margin=Decimal("0.5"), max_dd_gate_pct=Decimal("10"))
        w = sustainable_withdrawal(
            avg_monthly_return=-0.02, max_dd=Decimal("2"), equity=Decimal("100000"), config=config
        )
        assert w == Decimal("0")
