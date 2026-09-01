"""Sella registros de magic aportados por el operador e inventaría EAs reales.

La asociación exige una coincidencia única de versión entre el registro y un
``.ex5`` instalado en el terminal indicado. No modifica MT5 ni crea bots F7.
Los magics duplicados dentro de una misma cuenta quedan retenidos en el
manifiesto, porque no permiten atribuir historial por bot de forma inequívoca.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

import core.db.models  # noqa: F401
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.models.accounts import Account
from core.db.models.operations import ExternalEaInventory
from core.services.admin_imports import _artifact_metadata, _get_or_create_artifact


@dataclass(frozen=True)
class Record:
    strategy_name: str
    comment_identity: str
    magic_number: int
    symbol: str | None
    timeframe: str | None


def _version(value: str) -> str | None:
    matches = re.findall(r"\d+\.\d+\.\d+", value)
    return matches[-1] if matches else None


def _parse_bepb(text: str) -> list[Record]:
    pattern = re.compile(
        r"Estrategia\s+\d+:\s*(?P<name>.+?)\s*\((?P<symbol>[^,]+),(?P<tf>[^)]+)\)\s*\n"
        r"CustomComment:\s*(?P<comment>[^|\r\n]+)\s*\|\s*MagicNumber:\s*(?P<magic>\d+)",
        re.IGNORECASE,
    )
    return [Record(m.group("name").strip(), m.group("comment").strip(), int(m.group("magic")),
                   m.group("symbol").strip(), m.group("tf").strip()) for m in pattern.finditer(text)]


def _parse_jjti(text: str) -> list[Record]:
    pattern = re.compile(
        r"ESTRATEGIA\s+\d+:\s*(?P<name>[^\r\n]+).*?^Identificadores:\s*(?P<comment>[^\r\n]+).*?^MagicNumber:\s*(?P<magic>\d+)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    records: list[Record] = []
    for match in pattern.finditer(text):
        name = match.group("name").strip()
        market = re.search(r"\b(?P<symbol>[A-Z]{6}|[A-Z]+\d*)\s+(?P<timeframe>M\d+|H\d+|D\d|DAILY)\b", name, re.IGNORECASE)
        symbol = market.group("symbol") if market else None
        timeframe = market.group("timeframe").upper() if market else None
        records.append(Record(name, match.group("comment").strip(), int(match.group("magic")), symbol, timeframe))
    return records


def parse_records(path: Path, account_label: str) -> list[Record]:
    text = path.read_text(encoding="utf-8-sig")
    records = _parse_bepb(text) if account_label.upper() == "BEPB" else _parse_jjti(text)
    if not records:
        raise ValueError(f"no se pudieron extraer registros de {path.name}")
    return records


def _walk_experts(target: object, relative: str = "Experts", depth: int = 0) -> Iterable[tuple[str, int]]:
    if depth > 5:
        return
    absolute = target.ruta_absoluta(relative)
    for entry in target.listar_dir(absolute):
        child = f"{relative}/{entry['nombre']}"
        if entry["es_dir"]:
            yield from _walk_experts(target, child, depth + 1)
        elif entry["nombre"].lower().endswith(".ex5"):
            yield child, int(entry["tamano"])


def _candidate_for(record: Record, files: list[str], target: object) -> tuple[str | None, str, str | None]:
    version = _version(record.strategy_name) or _version(record.comment_identity)
    if version is None:
        return None, "WITHHELD_NO_VERSION", None
    matched = [path for path in files if version in Path(path).stem]
    if len(matched) == 1:
        selected = matched[0]
        return selected, "MATCHED_UNIQUE_VERSION", hashlib.sha256(target.leer_bytes(target.ruta_absoluta(selected))).hexdigest()
    if not matched:
        return None, "WITHHELD_NO_DEPLOYED_EX5_MATCH", None
    digests = {path: hashlib.sha256(target.leer_bytes(target.ruta_absoluta(path))).hexdigest() for path in matched}
    if len(set(digests.values())) == 1:
        selected = min(matched, key=lambda candidate: (candidate.count("/"), len(candidate), candidate))
        return selected, "MATCHED_EQUIVALENT_EX5_COPIES", digests[selected]
    return None, "WITHHELD_AMBIGUOUS_DEPLOYED_EX5", None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-root", type=Path)
    parser.add_argument("--terminal-alias", required=True)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--account-label", choices=("JJTI", "BEPB"), required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--existing-manifest", type=Path,
                        help="Reutiliza un manifiesto sellado ya escaneado; no abre SSH.")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def persist(args: argparse.Namespace, rows: list[dict[str, object]], evidence_sha256: str) -> int:
    if get_settings().deployment_profile != "operational":
        raise RuntimeError("inventario externo permitido sólo en DEPLOYMENT_PROFILE=operational")
    accepted = [row for row in rows if str(row["status"]).startswith("MATCHED_")]
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == args.account_login))
        if account is None:
            raise ValueError("cuenta no registrada")
        await _get_or_create_artifact(
            session, kind="MT5_EA_MAGIC_RECORD", path=args.records, payload=args.records.read_bytes(),
            parser_version="external-ea-record-v1",
            metadata=_artifact_metadata(args.records, account_login=args.account_login, account_label=args.account_label,
                terminal_alias=args.terminal_alias, record_count=len(rows), evidence_sha256=evidence_sha256),
        )
        for row in accepted:
            session.add(ExternalEaInventory(
                account_id=account.id, bot_id=None, ea_filename=Path(str(row["ea_relative_path"])).name,
                ea_relative_path=str(row["ea_relative_path"]), ea_sha256=str(row["ea_sha256"]),
                comment_identity=str(row["comment_identity"]), magic_number=int(row["magic_number"]),
                symbol=row["symbol"], timeframe=row["timeframe"], observed_at=datetime.now(UTC),
            ))
        await session.commit()
    return len(accepted)


def main() -> None:
    args = parse_args()
    if not args.records.is_file():
        raise SystemExit("BLOQUEADO: falta el registro local de magics")
    evidence_sha256 = hashlib.sha256(args.records.read_bytes()).hexdigest()
    if args.existing_manifest is not None:
        manifest = json.loads(args.existing_manifest.read_text(encoding="utf-8"))
        if manifest.get("records_sha256") != evidence_sha256:
            raise SystemExit("BLOQUEADO: el manifiesto no corresponde al registro aportado")
        rows = manifest.get("records")
        if not isinstance(rows, list):
            raise SystemExit("BLOQUEADO: manifiesto sin registros")
    else:
        if args.bridge_root is None:
            raise SystemExit("BLOQUEADO: --bridge-root es obligatorio al escanear el terminal")
        sys.path.insert(0, str(args.bridge_root))
        from config import resolver_terminal  # type: ignore[import-not-found]
        from target import crear_target  # type: ignore[import-not-found]
        records = parse_records(args.records, args.account_label)
        duplicate_magics = {magic for magic, count in Counter(item.magic_number for item in records).items() if count > 1}
        target = crear_target(resolver_terminal(args.terminal_alias))
        files = [path for path, _ in _walk_experts(target)]
        rows = []
        for record in records:
            path, status, digest = _candidate_for(record, files, target)
            if record.magic_number in duplicate_magics:
                path, status = None, "WITHHELD_DUPLICATE_MAGIC_IN_ACCOUNT"
            rows.append({**asdict(record), "ea_relative_path": path, "ea_sha256": digest, "status": status})
        manifest = {
            "schema_version": 1, "created_at": datetime.now(UTC).isoformat(), "account_login": args.account_login,
            "account_label": args.account_label, "terminal_alias": args.terminal_alias, "records_sha256": evidence_sha256,
            "read_only_terminal_scan": True, "summary": dict(Counter(str(row["status"]) for row in rows)), "records": rows,
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    accepted = 0
    if args.apply:
        accepted = asyncio.run(persist(args, rows, evidence_sha256))
    print(json.dumps({"manifest": str(args.manifest), "summary": manifest["summary"], "persisted": accepted}, ensure_ascii=False))


if __name__ == "__main__":
    main()
