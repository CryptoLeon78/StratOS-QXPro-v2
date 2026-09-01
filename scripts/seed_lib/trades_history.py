"""PARTE 13: generador determinista de la historia de trades de los bots de
PRODUCCION (no de la cantera -- sus metricas de gate ya se siembran como
literales en bots_pipeline.py y no dependen de Trade reales, ver
ASSUMPTIONS G8).

No es una simulacion de mercado real: es un generador de propiedades
AGREGADAS -- reparte una curva mensual de retorno de portfolio (calibrada
para DD maximo/retorno medio/meses negativos) entre bots via un modelo de
un factor comun (induce la correlacion media pedida) + ruido idiosincrasico
por bot. Los recuentos totales de PARTE 13 (15.486 trades, 137.296 lotes)
se aproximan dentro de una tolerancia documentada, no se persiguen al
entero exacto -- lo que se verifica con assert duro son las propiedades
agregadas reales (formulas/trading.py::max_drawdown_pct, media de
retornos, nº de meses negativos, correlacion via services/correlations.py,
beta via formulas/portfolio.py::ols_alpha_beta)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np
from core.db.enums import TradeType
from core.db.models.accounts import Account
from core.db.models.market import IngestBatch, Trade
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from seed_lib.bots_production import ProductionBotSpec

TOTAL_TARGET_TRADES_PER_YEAR = 2_800  # ~15.486 trades / 5.53 anos -- ver ASSUMPTIONS G8
COMMON_FACTOR_LOADING = 1.0
IDIO_TO_COMMON_STD_RATIO = 0.85  # ~0.16 corr media medida contra el job real, ver ASSUMPTIONS G8

# bots_production.py::seed_production_bots -- Bot.risk_per_trade_pct=0.500
# es literal e identico para los 32 (no varia por spec). r_multiple =
# profit / (capital_base * RISK_PER_TRADE_PCT/100): aproximacion de "R" sin
# SL/tick real por simbolo (services/semaphore_sweep.py ya documenta que
# Trade.r_multiple nunca lo calcula el ingest real -- si se deja NULL en
# el seed, expectancy_r()/loss_streak()/page_hinkley() siempre caen al
# valor conservador 0/0/False para TODOS los bots, disparando AMARILLO en
# los 32 por igual via el chequeo `exp_rolling < exp_warn*exp_baseline`
# (0.0 siempre es menor que un umbral positivo) -- hallazgo real,
# verificado contra el sweep real tras el primer intento sin r_multiple,
# ver ASSUMPTIONS G8).
RISK_PER_TRADE_PCT = 0.5

# PARTE 13: "Lyra Scalper EURUSD ... correlacion 0,52 con Phoenix Scalper
# SPX" (criterio de aceptacion 9: par marcado redundante). El factor comun
# de portfolio por si solo no basta para acercar UN par especifico a un
# valor tan alto sin distorsionar la media general -- se les da un factor
# compartido EXTRA, solo entre ellos dos (ambos scalpers de alta
# frecuencia, plausible que compartan microestructura de mercado).
EXTRA_CORRELATED_PAIR = ("Lyra Scalper EURUSD", "Phoenix Scalper SPX")
EXTRA_PAIR_LOADING = 5.5


@dataclass(frozen=True)
class SeedPriceSpec:
    """Escala de precio exclusiva del fixture.

    Los precios no representan cotizaciones actuales ni se usan para tomar
    decisiones. Evitan que el backfill de R sobre datos sintéticos produzca
    distancias de SL imposibles en índices.
    """

    open_price: Decimal
    stop_distance: Decimal


SEED_PRICE_SPECS: dict[str, SeedPriceSpec] = {
    "EURUSD": SeedPriceSpec(Decimal("1.10000"), Decimal("0.01000")),
    "GBPUSD": SeedPriceSpec(Decimal("1.30000"), Decimal("0.01200")),
    "AUDUSD": SeedPriceSpec(Decimal("0.70000"), Decimal("0.00800")),
    "USDJPY": SeedPriceSpec(Decimal("150.000"), Decimal("1.500")),
    "XAUUSD": SeedPriceSpec(Decimal("2000.00"), Decimal("20.00")),
    "XAGUSD": SeedPriceSpec(Decimal("24.000"), Decimal("0.240")),
    "GDAXI": SeedPriceSpec(Decimal("18000.0"), Decimal("180.0")),
    "NDX": SeedPriceSpec(Decimal("18000.0"), Decimal("180.0")),
    "USTEC": SeedPriceSpec(Decimal("18000.0"), Decimal("180.0")),
    "SPX500": SeedPriceSpec(Decimal("5000.0"), Decimal("50.0")),
    "US30": SeedPriceSpec(Decimal("38000.0"), Decimal("380.0")),
    "USOIL": SeedPriceSpec(Decimal("75.00"), Decimal("0.75")),
}


def seed_prices_for_symbol(symbol: str) -> tuple[Decimal, Decimal, Decimal]:
    """Devuelve apertura, SL y TP simétricos para un símbolo del fixture."""
    spec = SEED_PRICE_SPECS[symbol]
    return (
        spec.open_price,
        spec.open_price - spec.stop_distance,
        spec.open_price + spec.stop_distance,
    )


@dataclass(frozen=True)
class GeneratedTrade:
    bot_id: int
    magic_number: int
    symbol: str
    trade_type: TradeType
    open_time: datetime
    close_time: datetime
    profit: Decimal
    r_multiple: Decimal = Decimal("0")


def trading_days(start: date, end: date) -> list[date]:
    """Dias L-V entre start y end (inclusive) -- MT5 no reporta trades de
    fin de semana en la inmensa mayoria de simbolos del roster."""
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def build_monthly_target_curve(
    n_months: int, target_mean_pct: float, n_negative_months: int, rng: np.random.Generator
) -> list[float]:
    """66 (o menos) retornos mensuales de PORTFOLIO que cumplen, por
    construccion: media == target_mean_pct y exactamente n_negative_months
    meses negativos. El rango de magnitudes de los meses negativos
    (-2.0%..-0.3%) fue calibrado empiricamente contra
    formulas/trading.py::max_drawdown_pct real hasta acercarse al DD
    maximo de PARTE 13 (4,8%) -- ver ASSUMPTIONS G8, no es un valor
    contractual, es el resultado de la calibracion."""
    n_negative = min(n_negative_months, n_months)
    n_positive = n_months - n_negative

    neg_vals = rng.uniform(-2.0, -0.3, size=n_negative) if n_negative else np.array([])
    pos_vals = rng.uniform(0.8, 5.5, size=n_positive) if n_positive else np.array([])

    if n_positive > 0:
        needed_pos_sum = target_mean_pct * n_months - neg_vals.sum()
        scale = needed_pos_sum / pos_vals.sum() if pos_vals.sum() != 0 else 1.0
        pos_vals = pos_vals * scale

    positions = sorted(rng.choice(n_months, size=n_negative, replace=False))
    sequence: list[float | None] = [None] * n_months
    shuffled_neg = list(neg_vals)
    rng.shuffle(shuffled_neg)
    for pos, val in zip(positions, shuffled_neg, strict=True):
        sequence[pos] = val

    shuffled_pos = list(pos_vals)
    rng.shuffle(shuffled_pos)
    pos_i = 0
    for i in range(n_months):
        if sequence[i] is None:
            sequence[i] = shuffled_pos[pos_i]
            pos_i += 1

    filled: list[float] = []
    for v in sequence:
        assert v is not None
        filled.append(v)
    return filled


def month_boundaries(start: date, end: date) -> list[tuple[date, date]]:
    boundaries: list[tuple[date, date]] = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        next_month = date(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1)
        month_end = min(next_month - timedelta(days=1), end)
        month_start = max(cursor, start)
        boundaries.append((month_start, month_end))
        cursor = next_month
    return boundaries


def generate_production_trades(
    roster: tuple[ProductionBotSpec, ...],
    bot_ids_by_name: dict[str, int],
    history_start: date,
    history_end: date,
    total_capital: Decimal,
    rng: np.random.Generator,
) -> list[GeneratedTrade]:
    """Genera mes a mes, no dia a dia -- hallazgo real de la primera
    version (dia a dia con `daily_trade_prob` independiente por bot): un
    bot de baja frecuencia solo "capturaba" el factor comun en los pocos
    dias que SI operaba, perdiendo la contribucion de los dias sin trade y
    quedando muy por debajo del retorno objetivo (verificado: DD real
    1,05% y retorno mensual 0,85% vs objetivos 4,8%/2,69%). Repartiendo la
    contribucion mensual OBJETIVO de cada bot (capital_base * retorno_mes
    * peso) entre los N trades que ese bot tiene ese mes -- sea cual sea
    N -- la suma mensual del bot converge al objetivo con independencia de
    su frecuencia de trading."""
    n_days = (history_end - history_start).days + 1
    n_years = max(n_days / 365.25, 1 / 365.25)
    boundaries = month_boundaries(history_start, history_end)
    n_months = max(1, len(boundaries))
    target_negative = round(14 * n_months / 66)
    monthly_curve = build_monthly_target_curve(n_months, 2.69, target_negative, rng)

    total_weight = sum(float(s.capital_pct) for s in roster) or 1.0
    target_total_trades = round(TOTAL_TARGET_TRADES_PER_YEAR * n_years)
    sum_expected_monthly = sum(s.expected_trades_30d for s in roster) or 1
    # PARTE 13 da "espera N trades/mes" por bot -- pero aplicado a TODA la
    # historia da ~2x el total objetivo (verificado: 495/mes * 66 meses ~=
    # 32.670 vs 15.486 objetivo) -- se escala la frecuencia real, no el
    # "esperado" contractual de cada bot (ese sigue intacto en Baseline,
    # es lo que consume watchdog.py para "observado vs esperado").
    frequency_scale = target_total_trades / (sum_expected_monthly * n_months)
    recent_cutoff = history_end - timedelta(days=45)
    extra_pair_factor = rng.normal(0.0, 1.0, size=n_months)  # ver EXTRA_CORRELATED_PAIR arriba

    trades: list[GeneratedTrade] = []
    for spec in roster:
        weight = float(spec.capital_pct) / total_weight
        capital_base = float(total_capital) * weight
        risk_amount = capital_base * (RISK_PER_TRADE_PCT / 100.0)
        bot_id = bot_ids_by_name[spec.name]
        expected_trades_month = max(0.3, spec.expected_trades_30d * frequency_scale)
        in_extra_pair = spec.name in EXTRA_CORRELATED_PAIR
        idio_ratio = IDIO_TO_COMMON_STD_RATIO * (0.22 if in_extra_pair else 1.0)
        idio_std_per_trade = capital_base * 0.004 * idio_ratio

        for month_index, (monthly_return_pct, (month_start, month_end)) in enumerate(
            zip(monthly_curve, boundaries, strict=True)
        ):
            month_days = trading_days(month_start, month_end)
            if not month_days:
                continue
            n_trades_month = int(rng.poisson(expected_trades_month))
            if n_trades_month == 0:
                continue

            target_month_pnl = capital_base * (monthly_return_pct / 100.0) * COMMON_FACTOR_LOADING
            if in_extra_pair:
                target_month_pnl += (
                    capital_base * extra_pair_factor[month_index] * 0.01 * EXTRA_PAIR_LOADING
                )
            multiplier = 1.0 if month_end < recent_cutoff else spec.underperformance_factor
            target_month_pnl *= multiplier

            per_trade_shares = rng.dirichlet(np.ones(n_trades_month))
            day_indices = rng.integers(0, len(month_days), size=n_trades_month)
            trade_days = [month_days[i] for i in day_indices]
            for share, day in zip(per_trade_shares, trade_days, strict=True):
                idio_component = rng.normal(0.0, idio_std_per_trade)
                profit_f = target_month_pnl * share + idio_component
                profit = Decimal(str(round(profit_f, 2)))
                # column_types.py::RMultiple = Numeric(8,4) -- clamp para no
                # desbordar la columna con un swing extremo del factor extra
                # de correlacion (EXTRA_PAIR_LOADING) ni mostrar un R
                # irrealmente grande (r_multiple es una aproximacion, ver
                # RISK_PER_TRADE_PCT arriba, no un valor de mercado real).
                r_raw = profit_f / risk_amount if risk_amount else 0.0
                r_multiple = Decimal(str(round(max(-20.0, min(20.0, r_raw)), 4)))
                open_dt = datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(
                    minutes=int(rng.integers(480, 1020))
                )
                close_dt = open_dt + timedelta(minutes=max(5, int(spec.avg_trade_duration_min)))
                trades.append(
                    GeneratedTrade(
                        bot_id=bot_id,
                        magic_number=spec.magic_number,
                        symbol=spec.market,
                        trade_type=TradeType.BUY if rng.random() < 0.5 else TradeType.SELL,
                        open_time=open_dt,
                        close_time=close_dt,
                        profit=profit,
                        r_multiple=r_multiple,
                    )
                )
    return trades


async def bulk_insert_trades(
    session: AsyncSession, account: Account, trades: list[GeneratedTrade], now: datetime
) -> tuple[int, int]:
    """Un IngestBatch sellado (ingest_seal real, no un hash inventado) por
    dia con trades, no uno por trade. Bulk-insert real (Core insert, no
    identity map de la ORM uno-a-uno) -- necesario para que 15k+ filas se
    siembren en segundos."""
    by_day: dict[date, list[GeneratedTrade]] = {}
    for trade in trades:
        by_day.setdefault(trade.open_time.date(), []).append(trade)

    batch_rows = []
    for day in sorted(by_day):
        day_trades = by_day[day]
        payload = [
            {
                "ticket_mt5": i,
                "symbol": t.symbol,
                "profit": str(t.profit),
                "open_time": t.open_time.isoformat(),
            }
            for i, t in enumerate(day_trades)
        ]
        server_ts = datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(hours=23)
        batch_rows.append(
            {
                "ts": server_ts,
                "connector_instance_id": account.connector_instance_id or "seed-generator",
                "account_id": account.id,
                "batch_type": "trades",
                "records": len(day_trades),
                "sha256": compute_batch_sha256(account.login, "trades", payload),
                "server_ts": server_ts,
            }
        )

    result = await session.execute(insert(IngestBatch).returning(IngestBatch.id), batch_rows)
    batch_ids = [row[0] for row in result.fetchall()]

    trade_rows = []
    ticket_seq = 3_000_000
    for (_day, day_trades), batch_id in zip(sorted(by_day.items()), batch_ids, strict=True):
        for t in day_trades:
            ticket_seq += 1
            open_price, sl, tp = seed_prices_for_symbol(t.symbol)
            trade_rows.append(
                {
                    "bot_id": t.bot_id,
                    "account_id": account.id,
                    "magic_number": t.magic_number,
                    "ticket_mt5": ticket_seq,
                    "symbol": t.symbol,
                    "open_time": t.open_time,
                    "close_time": t.close_time,
                    "type": t.trade_type,
                    "volume": Decimal("0.10"),
                    "open_price": open_price,
                    "close_price": open_price,
                    "sl": sl,
                    "tp": tp,
                    "profit": t.profit,
                    "commission": Decimal("0"),
                    "swap": Decimal("0"),
                    "r_multiple": t.r_multiple,
                    "ingest_batch_id": batch_id,
                    "ingested_at": now,
                }
            )

    if trade_rows:
        await session.execute(insert(Trade), trade_rows)

    return len(trade_rows), len(batch_rows)
