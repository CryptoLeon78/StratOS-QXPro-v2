"""Parser cerrado de artefactos SQX144 para baselines administrativas.

No infiere métricas ausentes y no depende de una ruta externa.  Sólo acepta
los miembros mínimos que StrategyQuant X exporta para una estrategia y los
registros de órdenes completos del formato SQOrderFileFormat:11.
"""

from __future__ import annotations

import io
import re
import struct
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite

PARSER_VERSION = "sqx144-orders-v1"
_MAX_ARTIFACT_BYTES = 50 * 1024 * 1024
_REQUIRED_MEMBERS = {"orders.bin", "strategy_Portfolio.xml", "lastSettings.xml"}
_MAGIC = (
    b"\x04\x03\x02\x01",
    b"\x03\x02\x04\x01",
    b"\x02\x03\x04\x01",
    b"\x03\x04\x02\x01",
    b"\x02\x04\x03\x01",
    b"\x04\x02\x03\x01",
    b"\x02\x03\x05\x01",
)


@dataclass(frozen=True)
class ParsedBaseline:
    build: str
    symbol: str
    timeframe: str
    backtest_from: str
    backtest_to: str
    profit_factor: float
    expectancy_r: float
    sharpe: float
    max_dd_pct: float
    win_rate: float
    payoff: float
    avg_trade_duration_min: float
    max_consec_losses: int
    expected_trades_30d: int
    trade_count: int


def _strip_java_blocks(raw: bytes) -> bytes:
    out = bytearray()
    pos = 4 if raw.startswith(b"\xac\xed\x00\x05") else 0
    while pos < len(raw):
        marker = raw[pos]
        if marker == 0x7A and pos + 5 <= len(raw):
            size = struct.unpack(">I", raw[pos + 1 : pos + 5])[0]
            end = pos + 5 + size
            if end > len(raw):
                raise ValueError("orders.bin truncado")
            out.extend(raw[pos + 5 : end])
            pos = end
        elif marker == 0x77 and pos + 2 <= len(raw):
            size = raw[pos + 1]
            end = pos + 2 + size
            if end > len(raw):
                raise ValueError("orders.bin truncado")
            out.extend(raw[pos + 2 : end])
            pos = end
        else:
            break
    return bytes(out)


def _parse_trades(raw: bytes) -> list[tuple[datetime, datetime, float]]:
    stream = _strip_java_blocks(raw)
    first = min((i for magic in _MAGIC if (i := stream.find(magic)) >= 0), default=-1)
    if first < 0:
        raise ValueError("orders.bin sin registros SQX reconocibles")
    rows: list[tuple[datetime, datetime, float]] = []
    for pos in range(first, len(stream) - 148, 149):
        record = stream[pos : pos + 149]
        if record[:4] not in _MAGIC:
            break
        opened, closed = struct.unpack(">qq", record[15:23] + record[44:52])
        pnl = struct.unpack(">f", record[66:70])[0]
        if closed < opened or not isfinite(pnl):
            raise ValueError("registro SQX inválido")
        rows.append(
            (
                datetime.fromtimestamp(opened / 1000, UTC),
                datetime.fromtimestamp(closed / 1000, UTC),
                pnl,
            )
        )
    if not rows:
        raise ValueError("orders.bin no contiene trades completos")
    return rows


def parse_sqx144_baseline(payload: bytes) -> ParsedBaseline:
    if not 0 < len(payload) <= _MAX_ARTIFACT_BYTES or not zipfile.is_zipfile(io.BytesIO(payload)):
        raise ValueError("artefacto SQX inválido o supera el límite administrativo")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            name.startswith(("/", "\\")) or ".." in name.split("/") for name in names
        ):
            raise ValueError("estructura ZIP insegura")
        if not _REQUIRED_MEMBERS.issubset(names):
            raise ValueError("faltan miembros SQX requeridos")
        if sum(info.file_size for info in archive.infolist()) > _MAX_ARTIFACT_BYTES:
            raise ValueError("SQX descomprimido supera el límite")
        strategy = archive.read("strategy_Portfolio.xml").decode("utf-8", errors="strict")
        settings = archive.read("lastSettings.xml").decode("utf-8", errors="strict")
        trades = _parse_trades(archive.read("orders.bin"))
    build = re.search(r'AppVersion="([^"]+)"', strategy)
    chart = re.search(r'<Chart symbol="([^"]+)" timeframe="([^"]+)"', settings)
    period = re.search(r'<Setup dateFrom="([^"]+)" dateTo="([^"]+)"', settings)
    capital_match = re.search(r"<InitialCapital>([^<]+)</InitialCapital>", settings)
    if (
        not build
        or not re.fullmatch(r"SQX Build 144\.\d+", build.group(1))
        or not chart
        or not period
        or not capital_match
    ):
        raise ValueError("SQX144 o metadatos de backtest no verificables")
    try:
        starting_capital = float(capital_match.group(1))
    except ValueError as exc:
        raise ValueError("InitialCapital SQX inválido") from exc
    if not isfinite(starting_capital) or starting_capital <= 0:
        raise ValueError("InitialCapital SQX inválido")
    pnl = [row[2] for row in trades]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x < 0]
    if not wins or not losses:
        raise ValueError("métricas incompletas: se requieren ganancias y pérdidas")
    gross_win, gross_loss = sum(wins), abs(sum(losses))
    avg_loss = gross_loss / len(losses)
    equity, peak, dd = starting_capital, starting_capital, 0.0
    for value in pnl:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, (peak - equity) / peak * 100 if peak else 0)
    span_days = max((trades[-1][1] - trades[0][0]).total_seconds() / 86400, 1.0)
    current = longest = 0
    for value in pnl:
        current = current + 1 if value < 0 else 0
        longest = max(longest, current)
    returns = [value / starting_capital for value in pnl]
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / max(len(returns) - 1, 1)
    sharpe = mean / variance**0.5 * (len(trades) / (span_days / 365.25)) ** 0.5 if variance else 0.0
    values = (gross_win / gross_loss, (sum(pnl) / len(pnl)) / avg_loss, sharpe, dd)
    if not all(isfinite(value) for value in values):
        raise ValueError("métricas SQX no finitas")
    return ParsedBaseline(
        build.group(1),
        chart.group(1),
        chart.group(2),
        period.group(1).replace(".", "-"),
        period.group(2).replace(".", "-"),
        values[0],
        values[1],
        values[2],
        values[3],
        len(wins) / len(pnl),
        (gross_win / len(wins)) / avg_loss,
        sum((close - opened).total_seconds() / 60 for opened, close, _ in trades) / len(trades),
        longest,
        max(1, round(len(trades) / span_days * 30)),
        len(trades),
    )
