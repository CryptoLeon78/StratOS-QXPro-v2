from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from core.db.enums import ChecklistType
from core.db.models.governance import WithdrawalLog
from core.services.withdrawals import (
    WithdrawalServiceConfig,
    calculate,
    register_withdrawal,
)
from tests.factories import AccountFactory, ChecklistRunFactory, EquitySnapshotFactory

CONFIG = WithdrawalServiceConfig(safety_margin=Decimal("1.0"), max_dd_gate_pct=Decimal("8"))


async def _real_account(db_session: object) -> object:
    account = AccountFactory(is_demo=False)
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account


class TestCalculate:
    async def test_positive_trend_yields_positive_withdrawal(self, db_session: object) -> None:
        account = await _real_account(db_session)
        now = datetime.now(UTC)
        equity = Decimal("30000")
        for i in range(30):
            db_session.add(  # type: ignore[attr-defined]
                EquitySnapshotFactory(
                    account_id=account.id, ts=now - timedelta(days=30 - i), equity=equity
                )
            )
            equity *= Decimal("1.001")
        await db_session.flush()  # type: ignore[attr-defined]

        amount = await calculate(db_session, CONFIG, now)  # type: ignore[arg-type]
        assert amount > 0

    async def test_negative_trend_yields_zero(self, db_session: object) -> None:
        account = await _real_account(db_session)
        now = datetime.now(UTC)
        equity = Decimal("30000")
        for i in range(30):
            db_session.add(  # type: ignore[attr-defined]
                EquitySnapshotFactory(
                    account_id=account.id, ts=now - timedelta(days=30 - i), equity=equity
                )
            )
            equity *= Decimal("0.999")
        await db_session.flush()  # type: ignore[attr-defined]

        amount = await calculate(db_session, CONFIG, now)  # type: ignore[arg-type]
        assert amount == Decimal("0")

    async def test_no_data_yields_zero(self, db_session: object) -> None:
        amount = await calculate(db_session, CONFIG, datetime.now(UTC))  # type: ignore[arg-type]
        assert amount == Decimal("0")


class TestRegisterWithdrawal:
    async def test_raises_when_checklist_not_completed(self, db_session: object) -> None:
        checklist = ChecklistRunFactory(
            checklist_type=ChecklistType.MONTHLY, period_key="2026-08", completed=False
        )
        with pytest.raises(ValueError, match="checklist"):
            await register_withdrawal(
                db_session,
                Decimal("2500"),
                checklist,
                Decimal("180000"),
                datetime.now(UTC),  # type: ignore[arg-type]
            )

    async def test_persists_even_in_a_negative_month(self, db_session: object) -> None:
        # PARTE 14: "retiro mensual-nomina SIN EXCEPCION aunque el mes sea negativo".
        checklist = ChecklistRunFactory(
            checklist_type=ChecklistType.MONTHLY, period_key="2026-08", completed=True
        )
        db_session.add(checklist)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        log = await register_withdrawal(  # type: ignore[arg-type]
            db_session, Decimal("2500.00"), checklist, Decimal("180000.00"), datetime.now(UTC)
        )
        await db_session.commit()  # type: ignore[attr-defined]

        persisted = (
            await db_session.execute(select(WithdrawalLog).where(WithdrawalLog.id == log.id))  # type: ignore[attr-defined]
        ).scalar_one()
        assert persisted.amount == Decimal("2500.00")
