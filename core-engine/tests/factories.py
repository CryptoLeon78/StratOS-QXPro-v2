"""Factories `factory_boy` (PARTE 12 G1). Estilo `factory.Factory` puro
(no `SQLAlchemyModelFactory`): construyen la instancia en memoria, el test
hace `session.add(obj)` + `await session.commit()` — evita atar la factory a
una sesion sincrona, que no encaja con el engine async del proyecto.

Solo las tablas que los tests de G1 necesitan de verdad (Account, Bot,
Baseline, Trade, EquitySnapshot, IngestBatch, DecisionLog, SystemConfig); el
resto se factoriza cuando la fase que las usa (G2/G3) las necesite."""

import hashlib
from datetime import UTC, datetime
from decimal import Decimal

import factory

from core.db.enums import (
    ActorType,
    BaselineSource,
    BotProfile,
    BotRole,
    PipelinePhase,
    SemaphoreState,
    TradeType,
)
from core.db.models.accounts import Account, Baseline, Bot
from core.db.models.decisions import DecisionLog
from core.db.models.governance import SystemConfig
from core.db.models.market import EquitySnapshot, IngestBatch, Trade


class AccountFactory(factory.Factory):
    class Meta:
        model = Account

    name = factory.Sequence(lambda n: f"Account {n}")
    broker = "Darwinex"
    login = factory.Sequence(lambda n: str(100000 + n))
    server = "Darwinex-Live"
    currency = "EUR"
    is_demo = False
    connector_instance_id = None
    is_active = True


class BotFactory(factory.Factory):
    class Meta:
        model = Bot

    account_id = None  # el test lo rellena tras insertar el Account
    magic_number = factory.Sequence(lambda n: 118000 + n)
    name = factory.Sequence(lambda n: f"Bot {n}")
    market = "EURUSD"
    timeframe = "H1"
    profile = BotProfile.TREND
    role = BotRole.CHAMPION
    slot = None
    pipeline_phase = PipelinePhase.F7
    semaphore_state = SemaphoreState.VERDE
    entered_state_at = factory.LazyFunction(lambda: datetime.now(UTC))
    capital_allocated_pct = Decimal("4.00")
    risk_per_trade_pct = Decimal("0.500")
    sizing_multiplier = Decimal("1.00")
    sizing_current_pct = Decimal("100.00")
    kelly_fraction = Decimal("0.25")
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    baseline_id = None


class BaselineFactory(factory.Factory):
    class Meta:
        model = Baseline

    bot_id = None  # el test lo rellena tras insertar el Bot
    source = BaselineSource.BACKTEST
    profit_factor = 1.8
    expectancy_r = 0.2
    sharpe = 1.5
    max_dd_pct = Decimal("3.500")
    win_rate = 0.55
    payoff = 1.3
    avg_trade_duration_min = 240.0
    max_consec_losses = 5
    expected_trades_30d = 10
    dd_contract_pct = Decimal("4.000")
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    is_active = True


class IngestBatchFactory(factory.Factory):
    class Meta:
        model = IngestBatch

    ts = factory.LazyFunction(lambda: datetime.now(UTC))
    connector_instance_id = "connector-test-1"
    account_id = None  # el test lo rellena tras insertar el Account
    batch_type = "trades"
    records = 1
    sha256 = factory.LazyAttribute(
        lambda o: hashlib.sha256(f"{o.connector_instance_id}-{o.ts}".encode()).hexdigest()
    )
    server_ts = factory.LazyFunction(lambda: datetime.now(UTC))


class TradeFactory(factory.Factory):
    class Meta:
        model = Trade

    bot_id = None
    account_id = None
    magic_number = 118231
    ticket_mt5 = factory.Sequence(lambda n: 3000000 + n)
    symbol = "EURUSD"
    open_time = factory.LazyFunction(lambda: datetime.now(UTC))
    close_time = None
    type = TradeType.BUY
    volume = Decimal("0.10")
    open_price = Decimal("1.08500")
    close_price = None
    sl = Decimal("1.08000")
    tp = Decimal("1.09000")
    profit = Decimal("0.00")
    commission = Decimal("0.00")
    swap = Decimal("0.00")
    r_multiple = None
    ingest_batch_id = None
    ingested_at = factory.LazyFunction(lambda: datetime.now(UTC))


class EquitySnapshotFactory(factory.Factory):
    class Meta:
        model = EquitySnapshot

    ts = factory.LazyFunction(lambda: datetime.now(UTC))
    account_id = None
    equity = Decimal("179642.70")
    balance = Decimal("179642.70")
    drawdown_pct = Decimal("0.400")
    margin_level = 1500.0
    free_margin = Decimal("175000.00")


class DecisionLogFactory(factory.Factory):
    class Meta:
        model = DecisionLog

    ts = factory.LazyFunction(lambda: datetime.now(UTC))
    actor = ActorType.SYSTEM
    module = "semaphore"
    decision_type = "SEMAPHORE_TRANSITION"
    payload = factory.LazyFunction(dict)
    prev_hash = "0" * 64
    hash = factory.LazyFunction(lambda: hashlib.sha256(b"seed").hexdigest())


class SystemConfigFactory(factory.Factory):
    class Meta:
        model = SystemConfig

    key = factory.Sequence(lambda n: f"test_key_{n}")
    value = factory.LazyFunction(dict)
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
