"""Sella e importa el informe HTML de historial de MT5, sin heurísticas.

El informe debe contener las secciones ``Posiciones`` y ``Transacciones``.
Sólo se acepta una posición cerrada que reconcilie exactamente una entrada y
una salida. Si el HTML no expone magic number, el trade se persiste con
``magic_number=0`` (sentinela reservado) y ``bot_id=NULL``: queda huérfano
y auditable. El artefacto sellado declara explícitamente esa ausencia.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import core.db.models  # noqa: F401
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.enums import TradeType
from core.db.models.accounts import Account
from core.ingest.schemas import TradeIn, TradesIngestRequest
from core.ingest.services.trades import ingest_trades
from core.services.admin_imports import _artifact_metadata, _get_or_create_artifact
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select

UNRESOLVED_MAGIC_SENTINEL = 0

class HtmlRow(NamedTuple):
    cells: tuple[str, ...]


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[HtmlRow] = []
        self._cells: list[list[str]] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._cells = []
        elif tag in {"td", "th"} and self._cells is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cells is not None and self._cell is not None:
            self._cells.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._cells is not None:
            cells = tuple(" ".join("".join(cell).split()) for cell in self._cells)
            if cells:
                self.rows.append(HtmlRow(cells))
            self._cells = None
            self._cell = None


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _sections(rows: list[HtmlRow]) -> dict[str, list[HtmlRow]]:
    result: dict[str, list[HtmlRow]] = {"posiciones": [], "transacciones": []}
    active: str | None = None
    for row in rows:
        label = _normalized(" ".join(row.cells))
        if label in result:
            active = label
            continue
        if active is not None:
            result[active].append(row)
    return result


def _decimal(value: str) -> Decimal:
    compact = value.replace("\u00a0", "").replace(" ", "")
    if "," in compact and "." in compact:
        compact = compact.replace(".", "").replace(",", ".")
    elif "," in compact:
        compact = compact.replace(",", ".")
    try:
        return Decimal(compact)
    except InvalidOperation as exc:
        raise ValueError(f"decimal inválido: {value!r}") from exc


def _datetime(value: str, timezone: ZoneInfo) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone)


def _position_rows(rows: list[HtmlRow]) -> dict[str, dict[str, object]]:
    positions: dict[str, dict[str, object]] = {}
    for row in rows:
        cells = row.cells
        if len(cells) < 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if not cells[1].isdigit() or _normalized(cells[3]) not in {"buy", "sell"}:
            continue
        offset = 1 if len(cells) >= 14 else 0  # El comentario es una celda hidden tras type.
        positions[cells[1]] = {
            "open_time": cells[0], "position_id": cells[1], "symbol": cells[2], "type": cells[3],
            "volume": cells[4 + offset], "open_price": cells[5 + offset], "sl": cells[6 + offset],
            "tp": cells[7 + offset], "close_time": cells[8 + offset], "close_price": cells[9 + offset],
            "commission": cells[10 + offset], "swap": cells[11 + offset], "profit": cells[12 + offset],
        }
    return positions


def _transaction_rows(rows: list[HtmlRow]) -> list[dict[str, object]]:
    transactions: list[dict[str, object]] = []
    for row in rows:
        cells = row.cells
        if len(cells) < 14 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        if not cells[1].isdigit() or not cells[7].isdigit() or _normalized(cells[4]) not in {"in", "out"}:
            continue
        transactions.append({
            "time": cells[0], "deal_ticket": cells[1], "symbol": cells[2], "type": cells[3],
            "direction": cells[4], "volume": cells[5], "price": cells[6], "order": cells[7],
            "commission": cells[9], "swap": cells[11], "profit": cells[12],
        })
    return transactions


def parse_report(path: Path, source_timezone: str) -> tuple[str, list[TradeIn], Counter[str]]:
    try:
        timezone = ZoneInfo(source_timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"zona horaria IANA inválida: {source_timezone}") from exc
    payload = path.read_text(encoding="utf-16", errors="strict")
    parser = ReportParser()
    parser.feed(payload)
    account_match = re.search(r"<title>\s*(\d+)\s*:", payload, flags=re.IGNORECASE)
    if account_match is None:
        raise ValueError("no se pudo extraer la cuenta del título HTML")
    sections = _sections(parser.rows)
    positions = _position_rows(sections["posiciones"])
    transactions = _transaction_rows(sections["transacciones"])
    if not positions or not transactions:
        raise ValueError("HTML sin secciones Posiciones/Transacciones parseables")

    withheld: Counter[str] = Counter()
    trades: list[TradeIn] = []
    for position_id, position in positions.items():
        entries = [
            row for row in transactions
            if row["direction"] == "in" and row["order"] == position_id
        ]
        if len(entries) != 1:
            withheld["NON_UNIQUE_ENTRY"] += 1
            continue
        opened = entries[0]
        expected_exit_type = "sell" if _normalized(str(position["type"])) == "buy" else "buy"
        exits = [
            row for row in transactions
            if row["direction"] == "out"
            and row["symbol"] == position["symbol"]
            and _normalized(str(row["type"])) == expected_exit_type
            and _decimal(str(row["volume"])) == _decimal(str(position["volume"]))
            and row["time"] == position["close_time"]
            and _decimal(str(row["price"])) == _decimal(str(position["close_price"]))
        ]
        if len(exits) != 1:
            withheld["NON_UNIQUE_EXIT"] += 1
            continue
        closed = exits[0]
        if (
            opened["symbol"] != position["symbol"]
            or closed["symbol"] != position["symbol"]
            or _normalized(str(opened["type"])) != _normalized(str(position["type"]))
            or _decimal(str(opened["volume"])) != _decimal(str(position["volume"]))
        ):
            withheld["POSITION_TRANSACTION_MISMATCH"] += 1
            continue
        try:
            commission = _decimal(str(position["commission"]))
            swap = _decimal(str(position["swap"]))
            if commission != _decimal(str(opened["commission"])) + _decimal(str(closed["commission"])):
                withheld["COMMISSION_MISMATCH"] += 1
                continue
            if swap != _decimal(str(opened["swap"])) + _decimal(str(closed["swap"])):
                withheld["SWAP_MISMATCH"] += 1
                continue
            trades.append(TradeIn(
                # El ticket de posición está expuesto por la sección Posiciones y
                # es el identificador estable disponible para deduplicación. La
                # orden de salida no lo referencia en el HTML de MT5.
                ticket_mt5=int(position_id), symbol=str(position["symbol"]), magic_number=UNRESOLVED_MAGIC_SENTINEL,
                type=TradeType.BUY if _normalized(str(position["type"])) == "buy" else TradeType.SELL,
                volume=_decimal(str(position["volume"])), open_time=_datetime(str(position["open_time"]), timezone),
                close_time=_datetime(str(position["close_time"]), timezone), open_price=_decimal(str(position["open_price"])),
                close_price=_decimal(str(position["close_price"])), sl=None if not position["sl"] else _decimal(str(position["sl"])),
                tp=None if not position["tp"] else _decimal(str(position["tp"])), profit=_decimal(str(position["profit"])),
                commission=commission, swap=swap,
            ))
        except (ValueError, IndexError):
            withheld["INVALID_NUMERIC_OR_TIME"] += 1
    return account_match.group(1), trades, withheld


def load_time_reference(path: Path) -> dict[str, str]:
    try:
        reference = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"contrato temporal inválido: {path}") from exc
    required = ("broker_profile", "sqx_timezone", "iana_timezone", "mt5_timestamp_semantics")
    if any(not isinstance(reference.get(key), str) or not reference[key] for key in required):
        raise ValueError("contrato temporal incompleto")
    return {key: reference[key] for key in required}


async def run(args: argparse.Namespace) -> None:
    if get_settings().deployment_profile != "operational":
        raise SystemExit("importación permitida sólo en DEPLOYMENT_PROFILE=operational")
    time_reference = load_time_reference(args.time_reference)
    report_account, trades, withheld = parse_report(args.html, time_reference["iana_timezone"])
    if report_account != args.account_login:
        raise SystemExit(f"cuenta del informe {report_account} no coincide con --account-login")
    if not trades:
        raise SystemExit("sin posiciones reconciliadas; no se escribe nada")
    start, end = min(trade.open_time for trade in trades), max(trade.close_time for trade in trades)
    if not args.apply:
        print(f"planned account={report_account} timezone={time_reference['sqx_timezone']}->{time_reference['iana_timezone']} trades={len(trades)} window={start.isoformat()}..{end.isoformat()} withheld={dict(withheld)}")
        return
    payload = args.html.read_bytes()
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == args.account_login))
        if account is None:
            raise SystemExit("cuenta no registrada; alta F7 externa requerida antes de importar")
        artifact = await _get_or_create_artifact(
            session, kind="MT5_HISTORY_HTML", path=args.html, payload=payload, parser_version="mt5-html-history-v1",
            metadata=_artifact_metadata(args.html, account_login=args.account_login, time_reference=time_reference,
                window_start=start.isoformat(), window_end=end.isoformat(), reconciled_trades=len(trades),
                withheld_positions=dict(withheld), magic_number_status="ABSENT_UNRESOLVED",
                unresolved_magic_sentinel=UNRESOLVED_MAGIC_SENTINEL, trade_imported=True),
        )
        request_payload = {"account_login": args.account_login, "connector_instance_id": args.connector_instance_id,
                           "trades": [trade.model_dump(mode="json") for trade in trades]}
        request = TradesIngestRequest(**request_payload, batch_sha256=compute_batch_sha256(args.account_login, "trades", [request_payload]))
        outcome = await ingest_trades(session, account, request)
        await session.commit()
    print(f"artifact_id={artifact.id} accepted={outcome.accepted} duplicated={outcome.duplicated} reconciled={len(trades)} withheld={dict(withheld)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--time-reference", required=True, type=Path,
                        help="JSON sellable que enlaza zona SQX del broker y zona IANA")
    parser.add_argument("--connector-instance-id", default="mt5-html-history-import-v1")
    parser.add_argument("--apply", action="store_true")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
