"""Importa CSV del exportador read-only de historial MT5 de forma sellada.

Sólo acepta posiciones simples con una entrada y una salida. Las posiciones
parciales/múltiples se conservan fuera de la ingesta y se informan; no se
reconstruyen por heurística.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import core.db.models  # noqa: F401
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.enums import TradeType
from core.db.models.accounts import Account
from core.ingest.schemas import TradeIn, TradesIngestRequest
from core.ingest.services.trades import ingest_trades
from core.services.admin_imports import _get_or_create_artifact
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import select

ENTRY_IN = "0"
ENTRY_OUT = "1"
DEAL_BUY = "0"
DEAL_SELL = "1"


def load_time_reference(path: Path) -> dict[str, str]:
    reference = json.loads(path.read_text(encoding="utf-8"))
    required = ("broker_profile", "sqx_timezone", "iana_timezone", "mt5_timestamp_semantics")
    missing = [field for field in required if not reference.get(field)]
    if missing:
        raise ValueError(f"referencia temporal incompleta: {', '.join(missing)}")
    try:
        ZoneInfo(reference["iana_timezone"])
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"zona horaria IANA inválida: {reference['iana_timezone']}") from exc
    return reference


def _time(value: str, source_timezone: ZoneInfo) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S").replace(
        tzinfo=source_timezone
    ).astimezone(UTC)


def parse_closed_positions(path: Path, source_timezone: ZoneInfo) -> tuple[list[TradeIn], int]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            grouped[row["position_id"]].append(row)
    trades: list[TradeIn] = []
    withheld = 0
    for rows in grouped.values():
        entries = [row for row in rows if row["entry"] == ENTRY_IN]
        exits = [row for row in rows if row["entry"] == ENTRY_OUT]
        if len(entries) != 1 or len(exits) != 1:
            withheld += 1
            continue
        opened, closed = entries[0], exits[0]
        if opened["type"] not in {DEAL_BUY, DEAL_SELL} or opened["symbol"] != closed["symbol"]:
            withheld += 1
            continue
        trades.append(
            TradeIn(
                ticket_mt5=int(closed["deal_ticket"]),
                symbol=opened["symbol"],
                magic_number=int(opened["magic"]),
                type=TradeType.BUY if opened["type"] == DEAL_BUY else TradeType.SELL,
                volume=Decimal(opened["volume"]),
                open_time=_time(opened["time"], source_timezone),
                close_time=_time(closed["time"], source_timezone),
                open_price=Decimal(opened["price"]),
                close_price=Decimal(closed["price"]),
                profit=Decimal(closed["profit"]),
                commission=Decimal(closed["commission"]),
                swap=Decimal(closed["swap"]),
            )
        )
    return trades, withheld


async def run(args: argparse.Namespace) -> None:
    if get_settings().deployment_profile != "operational":
        raise SystemExit(
            "importación de histórico permitida sólo en DEPLOYMENT_PROFILE=operational"
        )
    time_reference = load_time_reference(args.time_reference)
    trades, withheld = parse_closed_positions(args.csv, ZoneInfo(time_reference["iana_timezone"]))
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == args.account_login))
        if account is None:
            raise SystemExit("cuenta no registrada; alta F7 antes de importar histórico")
        artifact = await _get_or_create_artifact(
            session,
            kind="MT5_HISTORY_CSV",
            path=args.csv,
            payload=args.csv.read_bytes(),
            parser_version="stratos-history-export-v1",
            metadata={
                "account_login": args.account_login,
                "connector_instance_id": args.connector_instance_id,
                "broker_profile": time_reference["broker_profile"],
                "sqx_timezone": time_reference["sqx_timezone"],
                "iana_timezone": time_reference["iana_timezone"],
                "timestamp_semantics": time_reference["mt5_timestamp_semantics"],
            },
        )
        payload = {
            "account_login": args.account_login,
            "connector_instance_id": args.connector_instance_id,
            "trades": [trade.model_dump(mode="json") for trade in trades],
        }
        request = TradesIngestRequest(
            **payload,
            batch_sha256=compute_batch_sha256(args.account_login, "trades", [payload]),
        )
        outcome = await ingest_trades(session, account, request)
        await session.commit()
    print(
        f"accepted={outcome.accepted} duplicated={outcome.duplicated} "
        f"withheld_positions={withheld} artifact_id={artifact.id} "
        f"timezone={time_reference['sqx_timezone']}->{time_reference['iana_timezone']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--connector-instance-id", required=True)
    parser.add_argument("--time-reference", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
