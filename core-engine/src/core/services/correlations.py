"""PARTE 7.5: matriz de correlaciones del portfolio (P&L diario). Envuelve
`correlation_matrix()` (formulas/portfolio.py, G2) con datos reales de
`Trade` cerrados y persiste 1 fila por par en `CorrelationMatrix`, cacheado
en Redis por (set de bots, ventana) tal como pide 7.5. Recalculo semanal
(domingo 06:00 UTC, contractual) via jobs/ + bajo demanda."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import combinations

import pandas as pd
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AccountDataOrigin, CorrelationSource
from core.db.models.accounts import Account
from core.db.models.governance import (
    CorrelationMatrix,
    CorrelationSnapshot,
    CorrelationSnapshotPair,
)
from core.db.models.market import Trade
from core.formulas.portfolio import correlation_matrix


@dataclass(frozen=True)
class CorrelationServiceConfig:
    window_days: int = 1240
    redundant_factor: float = 3.0
    ffill_limit: int = 3
    # 7.5, caso limite: "bot con <30 dias -> excluido con nota".
    min_days_for_correlation: int = 30
    # sin TTL contractual: recalculo semanal es el invalidador natural, este
    # es solo una red de seguridad si el job deja de correr (ASSUMPTIONS G5).
    cache_ttl_s: int = 8 * 24 * 3600


@dataclass(frozen=True)
class TradePnl:
    closed_at: datetime
    net_pnl: Decimal


@dataclass(frozen=True)
class CorrelationSnapshotResult:
    snapshot: CorrelationSnapshot
    created: bool


_SNAPSHOT_ALGORITHM_VERSION = "daily-net-pnl-v2"
_SNAPSHOT_STATUS_COMPLETED = "COMPLETED"
_SNAPSHOT_STATUS_WITHHELD = "WITHHELD"


def build_daily_pnl_by_bot(trades_by_bot: dict[int, list[TradePnl]]) -> dict[int, pd.Series]:
    result: dict[int, pd.Series] = {}
    for bot_id, trades in trades_by_bot.items():
        if not trades:
            result[bot_id] = pd.Series(dtype=float)
            continue
        frame = pd.DataFrame(
            {
                "date": [pd.Timestamp(t.closed_at.date()) for t in trades],
                "pnl": [float(t.net_pnl) for t in trades],
            }
        )
        result[bot_id] = frame.groupby("date")["pnl"].sum()
    return result


def _pair_correlations(corr: pd.DataFrame) -> dict[tuple[int, int], float]:
    """Extrae las correlaciones par a par (con signo) via posiciones numpy
    en vez de `.loc[bot_id, bot_id]` -- los stubs de pandas tipan `.loc` de
    forma demasiado generica para que mypy --strict reconozca el resultado
    como `SupportsFloat`; `ndarray.item()` si lo hace."""
    bot_ids: list[int] = sorted(int(c) for c in corr.columns)
    ordered = corr.reindex(index=bot_ids, columns=bot_ids)
    values = ordered.to_numpy(dtype=float)
    return {
        (bot_ids[i], bot_ids[j]): values[i, j].item()
        for i, j in combinations(range(len(bot_ids)), 2)
    }


def classify_redundant_pairs(
    corr: pd.DataFrame, redundant_factor: float
) -> dict[tuple[int, int], bool]:
    """ "Celda redundante (>3x media)" (7.5): la media es de las
    correlaciones absolutas fuera de la diagonal. Un par con varianza cero
    produce NaN en `corr` (Pearson indefinida) -- una comparacion con NaN
    siempre es False en Python, asi que nunca se marca redundante por error
    (el "n/a" de 7.5 lo interpreta la capa de API/UI a partir del NaN
    persistido, no este clasificador)."""
    pair_abs_corr = {pair: abs(value) for pair, value in _pair_correlations(corr).items()}
    if not pair_abs_corr:
        return {}
    mean_abs = sum(pair_abs_corr.values()) / len(pair_abs_corr)
    threshold = mean_abs * redundant_factor
    return {pair: value > threshold for pair, value in pair_abs_corr.items()}


async def _fetch_closed_trades(
    session: AsyncSession, window_start: datetime
) -> dict[int, list[TradePnl]]:
    rows = (
        await session.execute(
            select(Trade.bot_id, Trade.close_time, Trade.profit, Trade.commission, Trade.swap)
            .where(Trade.close_time.is_not(None), Trade.close_time >= window_start)
            .where(Trade.bot_id.is_not(None))
        )
    ).all()
    trades_by_bot: dict[int, list[TradePnl]] = {}
    for bot_id, close_time, profit, commission, swap in rows:
        trades_by_bot.setdefault(bot_id, []).append(
            TradePnl(closed_at=close_time, net_pnl=profit + commission + swap)
        )
    return trades_by_bot


def _canonical_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


async def _persist_source_snapshot(
    session: AsyncSession,
    *,
    source: CorrelationSource,
    now: datetime,
    window_start: datetime | None,
    window_end: datetime | None,
    window_days: int,
    account_scope: dict[str, object],
    input_manifest: dict[str, object],
    trades_by_bot: dict[int, list[TradePnl]],
    config: CorrelationServiceConfig,
) -> CorrelationSnapshotResult:
    """Sella y persiste un cálculo homogéneo sin reutilizar la matriz legacy."""
    input_sha256 = _canonical_hash(
        {
            "source": source.value,
            "algorithm_version": _SNAPSHOT_ALGORITHM_VERSION,
            "window_days": window_days,
            "account_scope": account_scope,
            "input_manifest": input_manifest,
        }
    )
    existing = await session.scalar(
        select(CorrelationSnapshot).where(
            CorrelationSnapshot.source == source,
            CorrelationSnapshot.input_sha256 == input_sha256,
        )
    )
    if existing is not None:
        return CorrelationSnapshotResult(snapshot=existing, created=False)

    daily = build_daily_pnl_by_bot(trades_by_bot)
    included = {
        bot_id: series
        for bot_id, series in daily.items()
        if len(series) >= config.min_days_for_correlation
    }
    if len(included) < 2:
        snapshot = CorrelationSnapshot(
            source=source,
            status=_SNAPSHOT_STATUS_WITHHELD,
            reason="INSUFFICIENT_HOMOGENEOUS_SERIES",
            created_at=now,
            window_start=window_start,
            window_end=window_end,
            window_days=window_days,
            algorithm_version=_SNAPSHOT_ALGORITHM_VERSION,
            account_scope=account_scope,
            input_manifest=input_manifest,
            input_sha256=input_sha256,
        )
        session.add(snapshot)
        await session.flush()
        return CorrelationSnapshotResult(snapshot=snapshot, created=True)

    corr = correlation_matrix(included, ffill_limit=config.ffill_limit)
    values = _pair_correlations(corr)
    redundant = classify_redundant_pairs(corr, config.redundant_factor)
    snapshot = CorrelationSnapshot(
        source=source,
        status=_SNAPSHOT_STATUS_COMPLETED,
        reason=None,
        created_at=now,
        window_start=window_start,
        window_end=window_end,
        window_days=window_days,
        algorithm_version=_SNAPSHOT_ALGORITHM_VERSION,
        account_scope=account_scope,
        input_manifest=input_manifest,
        input_sha256=input_sha256,
    )
    session.add(snapshot)
    await session.flush()
    for (bot_a_id, bot_b_id), correlation_value in values.items():
        if pd.isna(correlation_value):
            continue
        session.add(
            CorrelationSnapshotPair(
                snapshot_id=snapshot.id,
                bot_a_id=bot_a_id,
                bot_b_id=bot_b_id,
                correlation=correlation_value,
                is_redundant_pair=redundant[(bot_a_id, bot_b_id)],
            )
        )
    await session.flush()
    return CorrelationSnapshotResult(snapshot=snapshot, created=True)


async def run_mt5_real_correlation_snapshot(
    session: AsyncSession,
    config: CorrelationServiceConfig,
    now: datetime,
) -> CorrelationSnapshotResult:
    """Calcula sólo trades cerrados asignados de cuentas ``BROKER_REAL``.

    Los huérfanos se excluyen de forma explícita: sin identidad de bot no
    pueden participar en una correlación por estrategia. Fixture y demo no
    se consultan ni siquiera como relleno de serie.
    """
    window_start = now - timedelta(days=config.window_days)
    rows = (
        await session.execute(
            select(
                Trade.id,
                Trade.bot_id,
                Trade.close_time,
                Trade.profit,
                Trade.commission,
                Trade.swap,
                Trade.account_id,
            )
            .join(Account, Account.id == Trade.account_id)
            .where(Account.data_origin == AccountDataOrigin.BROKER_REAL)
            .where(Trade.close_time.is_not(None), Trade.close_time >= window_start)
            .where(Trade.bot_id.is_not(None))
            .order_by(Trade.id.asc(), Trade.close_time.asc())
        )
    ).all()
    trades_by_bot: dict[int, list[TradePnl]] = {}
    input_rows: list[dict[str, object]] = []
    account_ids: set[int] = set()
    for trade_id, bot_id, close_time, profit, commission, swap, account_id in rows:
        account_ids.add(account_id)
        net_pnl = profit + commission + swap
        trades_by_bot.setdefault(bot_id, []).append(TradePnl(closed_at=close_time, net_pnl=net_pnl))
        input_rows.append(
            {
                "trade_id": trade_id,
                "bot_id": bot_id,
                "account_id": account_id,
                "closed_at": close_time.isoformat(),
                "profit": str(profit),
                "commission": str(commission),
                "swap": str(swap),
            }
        )
    return await _persist_source_snapshot(
        session,
        source=CorrelationSource.MT5_REAL,
        now=now,
        window_start=window_start,
        window_end=now,
        window_days=config.window_days,
        account_scope={
            "data_origin": AccountDataOrigin.BROKER_REAL.value,
            "account_ids": sorted(account_ids),
        },
        input_manifest={"trades": input_rows},
        trades_by_bot=trades_by_bot,
        config=config,
    )


async def persist_mt5_backtest_correlation_snapshot(
    session: AsyncSession,
    *,
    now: datetime,
    window_start: datetime | None,
    window_end: datetime | None,
    window_days: int,
    input_manifest: dict[str, object],
    trades_by_bot: dict[int, list[TradePnl]],
    config: CorrelationServiceConfig,
) -> CorrelationSnapshotResult:
    """Entrada para el importador sellado de Tester; no acepta trades reales."""
    return await _persist_source_snapshot(
        session,
        source=CorrelationSource.MT5_BACKTEST,
        now=now,
        window_start=window_start,
        window_end=window_end,
        window_days=window_days,
        account_scope={"data_origin": "MT5_TESTER_SEALED_ARTIFACT"},
        input_manifest=input_manifest,
        trades_by_bot=trades_by_bot,
        config=config,
    )


def _cache_key(bot_ids: list[int], window_days: int) -> str:
    return f"corr:{','.join(str(b) for b in sorted(bot_ids))}:{window_days}"


async def run_correlation_job(
    session: AsyncSession, redis: Redis, config: CorrelationServiceConfig, now: datetime
) -> None:
    window_start = now - timedelta(days=config.window_days)
    trades_by_bot = await _fetch_closed_trades(session, window_start)

    returns_by_bot = build_daily_pnl_by_bot(trades_by_bot)
    included = {
        bot_id: series
        for bot_id, series in returns_by_bot.items()
        if len(series) >= config.min_days_for_correlation
    }
    if len(included) < 2:
        return

    corr = correlation_matrix(included, ffill_limit=config.ffill_limit)
    pair_correlations = _pair_correlations(corr)
    redundant = classify_redundant_pairs(corr, config.redundant_factor)

    cache_payload = []
    for (bot_a_id, bot_b_id), is_redundant in redundant.items():
        correlation_value = pair_correlations[(bot_a_id, bot_b_id)]
        session.add(
            CorrelationMatrix(
                ts=now,
                bot_a_id=bot_a_id,
                bot_b_id=bot_b_id,
                correlation=correlation_value,
                is_redundant_pair=is_redundant,
                window_days=config.window_days,
            )
        )
        cache_payload.append(
            {
                "bot_a_id": bot_a_id,
                "bot_b_id": bot_b_id,
                "correlation": correlation_value,
                "is_redundant_pair": is_redundant,
            }
        )
    await session.flush()

    await redis.set(
        _cache_key(list(included.keys()), config.window_days),
        json.dumps(cache_payload),
        ex=config.cache_ttl_s,
    )
