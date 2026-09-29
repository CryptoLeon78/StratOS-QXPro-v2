"""ADR 0013: cada endpoint de lectura con `?account_id=` devuelve solo datos
de esa cuenta. Escenario: cuenta A (real) y cuenta B (demo), cada una con su
equity, bot, posicion abierta, evento de KS y fase UMS; mas una alerta y una
decision de portfolio (account_id NULL) visibles desde cualquier cuenta."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import AccountDataOrigin, AlertLevel, DecisionStatus
from core.db.models.decisions import Alert, Decision
from core.db.models.governance import UmsPhaseLog
from tests.factories import (
    AccountFactory,
    BotFactory,
    EquitySnapshotFactory,
    IngestBatchFactory,
    KillSwitchEventFactory,
    TradeFactory,
)


@dataclass
class Scenario:
    a: int
    b: int
    bot_a: int
    bot_b: int


@pytest_asyncio.fixture
async def scenario(db_connection: AsyncConnection) -> Scenario:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    now = datetime.now(UTC)
    acc_a = AccountFactory(is_demo=False, name="CuentaA", data_origin=AccountDataOrigin.BROKER_REAL)
    acc_b = AccountFactory(is_demo=True, name="CuentaB", data_origin=AccountDataOrigin.BROKER_DEMO)
    session.add_all([acc_a, acc_b])
    await session.flush()
    bot_a = BotFactory(account_id=acc_a.id)
    bot_b = BotFactory(account_id=acc_b.id)
    session.add_all([bot_a, bot_b])
    await session.flush()
    for account, equity in ((acc_a, Decimal("100000")), (acc_b, Decimal("5000"))):
        session.add(
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=2), equity=equity, balance=equity
            )
        )
        session.add(EquitySnapshotFactory(account_id=account.id, ts=now, equity=equity))
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        bot = bot_a if account is acc_a else bot_b
        session.add(
            TradeFactory(
                account_id=account.id,
                bot_id=bot.id,
                magic_number=bot.magic_number,
                ingest_batch_id=batch.id,
            )
        )
    session.add(KillSwitchEventFactory(level=2, account_id=acc_a.id))
    session.add(
        UmsPhaseLog(
            ts=now,
            phase=3,
            equity_at=Decimal("100000"),
            metrics={},
            ready_to_advance=True,
            signed_by="op",
            account_id=acc_a.id,
        )
    )
    for account_id, label in ((acc_a.id, "A"), (acc_b.id, "B"), (None, "PORTFOLIO")):
        session.add(
            Alert(ts=now, level=AlertLevel.SUAVE, module="t", message=label, account_id=account_id)
        )
        session.add(
            Decision(
                ts=now,
                module="t",
                title=label,
                description=label,
                instruction_text=label,
                status=DecisionStatus.PENDING,
                account_id=account_id,
            )
        )
    await session.commit()
    return Scenario(a=acc_a.id, b=acc_b.id, bot_a=bot_a.id, bot_b=bot_b.id)


async def test_unknown_account_is_404(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/header/summary?account_id=999999")
    assert response.status_code == 404


async def test_header_is_scoped_to_the_account(api_client: AsyncClient, scenario: Scenario) -> None:
    a = (await api_client.get(f"/api/v1/header/summary?account_id={scenario.a}")).json()
    b = (await api_client.get(f"/api/v1/header/summary?account_id={scenario.b}")).json()

    assert Decimal(a["equity_eur"]) == Decimal("100000")
    assert Decimal(b["equity_eur"]) == Decimal("5000")
    assert a["open_positions"] == 1 and b["open_positions"] == 1
    assert a["ks_level"] == 2 and b["ks_level"] == 0
    # cuenta + portfolio (NULL), nunca la de la otra cuenta
    assert a["alerts"] == 2 and b["alerts"] == 2
    assert a["pending_decisions"] == 2 and b["pending_decisions"] == 2


async def test_equity_curve_of_a_demo_account_is_not_empty(
    api_client: AsyncClient, scenario: Scenario
) -> None:
    body = (await api_client.get(f"/api/v1/summary/equity-curve?account_id={scenario.b}")).json()
    assert [Decimal(p["equity"]) for p in body][-1] == Decimal("5000")


@pytest.mark.parametrize("path", ["alerts", "decisions"])
async def test_alerts_and_decisions_show_account_plus_portfolio(
    api_client: AsyncClient, scenario: Scenario, path: str
) -> None:
    body = (await api_client.get(f"/api/v1/{path}?account_id={scenario.a}")).json()
    labels = {row.get("message") or row.get("title") for row in body}
    assert labels == {"A", "PORTFOLIO"}


async def test_killswitch_and_ums_are_per_account(
    api_client: AsyncClient, scenario: Scenario
) -> None:
    ks_a = (await api_client.get(f"/api/v1/killswitch/status?account_id={scenario.a}")).json()
    ks_b = (await api_client.get(f"/api/v1/killswitch/status?account_id={scenario.b}")).json()
    assert ks_a["level"] == 2 and ks_b["level"] == 0

    ums_a = (await api_client.get(f"/api/v1/scaling/ums?account_id={scenario.a}")).json()
    ums_b = (await api_client.get(f"/api/v1/scaling/ums?account_id={scenario.b}")).json()
    assert ums_a["phase"] == 3 and ums_b is None


async def test_bots_dependent_endpoints_only_return_the_accounts_bots(
    api_client: AsyncClient, scenario: Scenario
) -> None:
    watchdog = (await api_client.get(f"/api/v1/execution/watchdog?account_id={scenario.a}")).json()
    assert [row["bot_id"] for row in watchdog] == [scenario.bot_a]

    heartbeat = (
        await api_client.get(f"/api/v1/execution/heartbeat?account_id={scenario.b}")
    ).json()
    assert [row["account_id"] for row in heartbeat] == [scenario.b]

    gaps = (await api_client.get(f"/api/v1/audit/continuity-gaps?account_id={scenario.a}")).json()
    assert [row["account_id"] for row in gaps] == [scenario.a]


async def test_exposure_and_seals_are_scoped(api_client: AsyncClient, scenario: Scenario) -> None:
    exposure = (await api_client.get(f"/api/v1/risk/exposure?account_id={scenario.a}")).json()
    assert len(exposure) == 1 and Decimal(exposure[0]["gross_volume"]) == Decimal("0.10")

    seals = (await api_client.get(f"/api/v1/audit/seals?account_id={scenario.a}")).json()
    assert seals["total_trades"] == 1 and seals["total_batches"] == 1

    provenance = (await api_client.get(f"/api/v1/data-provenance?account_id={scenario.b}")).json()
    assert [row["data_origin"] for row in provenance["accounts"]] == ["BROKER_DEMO"]
    assert provenance["trade_attribution"]["total"] == 1
