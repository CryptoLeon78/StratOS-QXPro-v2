"""Concilia los bots F7 de las cuentas reales con los EAs instalados en MT5.

Fuente de verdad: los gráficos con EA de cada terminal real
(`scan_mt5_chart_identity.py`) más el SHA-256 del `.ex5` que carga cada uno.
Decisión del operador (2026-10-13): lo instalado es lo que opera; lo que no
está instalado se retiró por decisión suya.

- EA instalado sin bot en su cuenta -> observación de inventario + alta F7
  externa (misma ruta que `register_external_f7_manifest.py`).
- Bot externo en F7/PRODUCCION sin EA instalado en su cuenta -> Cementerio con
  autopsia explícita (`apply_cemetery_archival`); nunca se borra.

No contacta MT5 ni el VPS: sólo lee los manifiestos ya escaneados.

Uso:
    python scripts/reconcile_real_bots_with_charts.py \
        --chart-scan scan_bepb.json --chart-scan scan_jjti.json \
        --ea-hashes ex5_hashes.json --account-label 4000055216=BEPB \
        --account-label 4000059903=JJTI --result result.json [--apply]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any

_RETIRABLE_PHASES = frozenset({"F7", "PRODUCCION"})


@dataclass(frozen=True)
class InstalledEa:
    account_login: str
    magic_number: int
    comment_identity: str
    ea_name: str
    symbol: str
    timeframe: str


@dataclass(frozen=True)
class BotRow:
    bot_id: int
    account_login: str
    magic_number: int
    name: str
    phase: str
    origin_kind: str


@dataclass(frozen=True)
class Plan:
    register: list[InstalledEa]
    retire: list[BotRow]
    kept: list[BotRow]


def load_installed(scan_paths: list[Path]) -> list[InstalledEa]:
    """EAs con magic de los manifiestos de escaneo; falla ante datos ambiguos."""
    installed: list[InstalledEa] = []
    for path in scan_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("profile_chart_id_conflicts"):
            raise SystemExit(f"{path.name}: conflictos de ID de gráfico, no se concilia")
        login = str(payload["account_login"])
        for chart in payload["charts"]:
            magic = chart.get("magic_number")
            if magic is None:
                continue
            fields = (chart.get("comment_identity"), chart.get("ea_filename"), chart.get("symbol"))
            if any(value in (None, "") for value in fields) or not chart.get("period"):
                raise SystemExit(f"{path.name}: gráfico incompleto magic={magic}")
            installed.append(
                InstalledEa(
                    account_login=login,
                    magic_number=int(magic),
                    comment_identity=str(chart["comment_identity"]),
                    ea_name=str(chart["ea_filename"]),
                    symbol=str(chart["symbol"]),
                    timeframe=str(chart["period"]),
                )
            )
    keys = [(ea.account_login, ea.magic_number) for ea in installed]
    if len(keys) != len(set(keys)):
        raise SystemExit("magic instalado dos veces en la misma cuenta; no se concilia")
    return installed


def build_plan(installed: list[InstalledEa], bots: list[BotRow], accounts: set[str]) -> Plan:
    """Plan puro: qué dar de alta y qué retirar en las cuentas indicadas."""
    installed_keys = {(ea.account_login, ea.magic_number) for ea in installed}
    bot_keys = {(bot.account_login, bot.magic_number) for bot in bots}
    register = [ea for ea in installed if (ea.account_login, ea.magic_number) not in bot_keys]
    retire: list[BotRow] = []
    kept: list[BotRow] = []
    for bot in bots:
        if bot.account_login not in accounts:
            continue
        if (bot.account_login, bot.magic_number) in installed_keys:
            kept.append(bot)
        elif bot.origin_kind == "EXTERNAL_PRODUCTION" and bot.phase in _RETIRABLE_PHASES:
            retire.append(bot)
    return Plan(register=register, retire=retire, kept=kept)


def manifest_records(
    register: list[InstalledEa], ea_hashes: dict[str, dict[str, dict[str, str]]]
) -> dict[str, list[dict[str, Any]]]:
    """Filas de manifiesto F7 por cuenta, con la ruta y el hash del `.ex5` real."""
    records: dict[str, list[dict[str, Any]]] = {}
    for ea in register:
        evidence = ea_hashes.get(ea.account_login, {}).get(str(ea.magic_number))
        if evidence is None:
            raise SystemExit(f"sin hash de .ex5 para {ea.account_login} magic={ea.magic_number}")
        if PureWindowsPath(evidence["relative_path"]).stem != ea.ea_name:
            raise SystemExit(f"el .ex5 no corresponde al gráfico: magic={ea.magic_number}")
        records.setdefault(ea.account_login, []).append(
            {
                "status": "MATCHED_UNIQUE_VERSION",
                "strategy_name": ea.comment_identity,
                "comment_identity": ea.comment_identity,
                "magic_number": ea.magic_number,
                "symbol": ea.symbol,
                "timeframe": ea.timeframe,
                "ea_relative_path": evidence["relative_path"],
                "ea_sha256": evidence["sha256"],
            }
        )
    return records


def autopsy_text(bot: BotRow, scan_sha: str, scanned_at: str) -> str:
    return (
        f"Retirado por decisión del operador (2026-10-13): el EA {bot.name} (magic "
        f"{bot.magic_number}) no está instalado en el terminal de la cuenta "
        f"{bot.account_login} según el escaneo de gráficos {scan_sha[:12]} ({scanned_at})."
    )


_LESSON = "Sin lección cuantitativa registrada: retirada discrecional del operador."


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chart-scan", action="append", required=True, type=Path)
    parser.add_argument("--ea-hashes", required=True, type=Path)
    parser.add_argument(
        "--account-label",
        action="append",
        required=True,
        help="login=ETIQUETA, p.ej. 4000055216=BEPB",
    )
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def _reconcile(args: argparse.Namespace) -> dict[str, Any]:
    import core.db.models  # noqa: F401
    from core.config import get_settings
    from core.db.base import async_session_factory
    from core.db.enums import CemeteryCause
    from core.db.models.accounts import Account, Bot
    from core.db.models.operations import ExternalEaInventory
    from core.redis import get_redis_client
    from core.state_machines.challenger import apply_cemetery_archival
    from sqlalchemy import select

    from register_external_f7_manifest import register_manifests

    if get_settings().deployment_profile != "operational":
        raise SystemExit("sólo en DEPLOYMENT_PROFILE=operational")

    labels = dict(item.split("=", 1) for item in args.account_label)
    installed = load_installed(args.chart_scan)
    scans = [json.loads(path.read_text(encoding="utf-8")) for path in args.chart_scan]
    scan_sha = hashlib.sha256(
        "".join(sorted(scan["payload_sha256"] for scan in scans)).encode()
    ).hexdigest()
    scanned_at = min(scan["created_at"] for scan in scans)
    ea_hashes = json.loads(args.ea_hashes.read_text(encoding="utf-8"))

    async with async_session_factory() as session:
        accounts = {
            account.id: account
            for account in (
                await session.execute(select(Account).where(Account.login.in_(list(labels))))
            ).scalars()
        }
        if set(labels) != {account.login for account in accounts.values()}:
            raise SystemExit("alguna cuenta indicada no existe en la base")
        bot_rows = [
            BotRow(
                bot_id=bot.id,
                account_login=accounts[bot.account_id].login,
                magic_number=bot.magic_number,
                name=bot.name,
                phase=bot.pipeline_phase.value,
                origin_kind=bot.origin_kind.value,
            )
            for bot in (
                await session.execute(select(Bot).where(Bot.account_id.in_(list(accounts))))
            ).scalars()
        ]
        plan = build_plan(installed, bot_rows, set(labels))
        records = manifest_records(plan.register, ea_hashes)
        result: dict[str, Any] = {
            "mode": "APPLY" if args.apply else "DRY_RUN",
            "chart_scan_sha256": scan_sha,
            "scanned_at": scanned_at,
            "register": [ea.__dict__ for ea in plan.register],
            "retire": [bot.__dict__ for bot in plan.retire],
            "kept": [bot.__dict__ for bot in plan.kept],
        }
        if not args.apply:
            return result

        login_to_id = {account.login: account_id for account_id, account in accounts.items()}
        now = datetime.now(UTC)
        for login, rows in records.items():
            for row in rows:
                session.add(
                    ExternalEaInventory(
                        account_id=login_to_id[login],
                        bot_id=None,
                        ea_filename=PureWindowsPath(row["ea_relative_path"]).name,
                        ea_relative_path=row["ea_relative_path"],
                        ea_sha256=row["ea_sha256"],
                        comment_identity=row["comment_identity"],
                        magic_number=row["magic_number"],
                        symbol=row["symbol"],
                        timeframe=row["timeframe"],
                        observed_at=now,
                    )
                )
        await session.commit()

    manifest_dir = args.result.parent / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifests: list[Path] = []
    for login, rows in records.items():
        path = manifest_dir / f"f7_manifest_{labels[login]}.json"
        path.write_text(
            json.dumps(
                {"account_login": login, "account_label": labels[login], "records": rows},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        manifests.append(path)
    if manifests:
        result["registration"] = await register_manifests(
            argparse.Namespace(manifest=manifests, result=args.result, apply=True)
        )

    redis = get_redis_client()
    async with async_session_factory() as session:
        for row in plan.retire:
            bot = await session.get(Bot, row.bot_id)
            if bot is None:
                raise SystemExit(f"bot {row.bot_id} desaparecido durante la conciliación")
            await apply_cemetery_archival(
                session,
                redis,
                bot,
                CemeteryCause.OTHER,
                autopsy_text(row, scan_sha, scanned_at),
                _LESSON,
            )
        await session.commit()
    return result


def main() -> None:
    args = _args()
    result = asyncio.run(_reconcile(args))
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "mode": result["mode"],
                "register": len(result["register"]),
                "retire": len(result["retire"]),
                "kept": len(result["kept"]),
            }
        )
    )


if __name__ == "__main__":
    main()
