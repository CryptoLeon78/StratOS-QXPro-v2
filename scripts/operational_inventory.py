"""Catálogo reproducible de artefactos operativos, sin asignar fases ficticias.

El modo normal sólo escribe un manifiesto JSON bajo ``runtime/operational``.
``--apply`` registra hechos y un evento append-only por artefacto en la base
operativa indicada por el entorno; no admite el perfil de fixture.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


MAGIC_PATTERN = re.compile(r"(?:MagicNumber|magic_number|Magic)\s*=\s*(\d+)")
TIMEFRAME_PATTERN = re.compile(r"(?:PERIOD_|InpWorkTF\s*=\s*)(M\d+|H\d+|D1|W1)")
BACKTEST_IDENTITY_PATTERN = re.compile(
    r"Backtested on\s+([^\s/]+)\s*/\s*(M\d+|H\d+|D1|W1)", re.IGNORECASE
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(path: Path) -> str:
    return path.stem.casefold().replace(" ", "")


def _mql5_identity(path: Path) -> tuple[int | None, str | None, str | None]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    magic = MAGIC_PATTERN.search(source)
    header = BACKTEST_IDENTITY_PATTERN.search(source)
    timeframe = TIMEFRAME_PATTERN.search(source)
    return (
        int(magic.group(1)) if magic else None,
        header.group(1) if header else None,
        header.group(2).upper() if header else (timeframe.group(1) if timeframe else None),
    )


def build_inventory(
    root: Path, source_group: str, *, source_root: str | None = None
) -> list[dict[str, object]]:
    from core.services.sqx_baseline_parser import parse_sqx144_baseline

    sqx = sorted(root.rglob("*.sqx"))
    mql5 = sorted(root.rglob("*.mq5"))
    by_key: dict[str, list[Path]] = defaultdict(list)
    for path in mql5:
        by_key[_key(path)].append(path)

    items: list[dict[str, object]] = []
    paired_mql5: set[Path] = set()
    for sqx_path in sqx:
        matches = by_key.get(_key(sqx_path), [])
        mql5_path = matches[0] if len(matches) == 1 else None
        if mql5_path:
            paired_mql5.add(mql5_path)
        magic, mql5_symbol, mql5_timeframe = (
            _mql5_identity(mql5_path) if mql5_path else (None, None, None)
        )
        parsed = None
        parse_error = None
        try:
            parsed = parse_sqx144_baseline(sqx_path.read_bytes())
        except Exception as exc:  # Parser fail-closed: no artefacto invalido entra a cola.
            parse_error = str(exc)
        identity_matches = (
            parsed is not None
            and mql5_symbol is not None
            and mql5_timeframe is not None
            and parsed.symbol == mql5_symbol
            and parsed.timeframe == mql5_timeframe
        )
        status = (
            "STATIC_VALIDATED"
            if mql5_path and magic is not None and parsed and identity_matches
            else "WITHHELD"
        )
        reason = None
        if not mql5_path:
            reason = "MQL5_PAIR_NOT_UNIQUE_OR_MISSING"
        elif magic is None:
            reason = "MQL5_MAGIC_MISSING"
        elif parse_error:
            reason = "SQX144_PARSE_FAILED"
        elif not identity_matches:
            reason = "SQX_MQL5_IDENTITY_MISMATCH"
        items.append(
            {
                "source_group": source_group,
                "source_root": source_root or str(root.resolve()),
                "sqx_path": str(sqx_path.resolve()),
                "mql5_path": str(mql5_path.resolve()) if mql5_path else None,
                "sqx_sha256": _sha256(sqx_path),
                "mql5_sha256": _sha256(mql5_path) if mql5_path else None,
                "strategy_name": sqx_path.stem,
                "magic_number": magic,
                "symbol": parsed.symbol if parsed else None,
                "mql5_symbol": mql5_symbol,
                "mql5_timeframe": mql5_timeframe,
                "timeframe": parsed.timeframe if parsed else mql5_timeframe,
                "status": status,
                "reason": reason,
            }
        )
    for mql5_path in mql5:
        if mql5_path in paired_mql5:
            continue
        magic, mql5_symbol, mql5_timeframe = _mql5_identity(mql5_path)
        items.append(
            {
                "source_group": source_group,
                "source_root": source_root or str(root.resolve()),
                "sqx_path": None,
                "mql5_path": str(mql5_path.resolve()),
                "sqx_sha256": None,
                "mql5_sha256": _sha256(mql5_path),
                "strategy_name": mql5_path.stem,
                "magic_number": magic,
                "mql5_symbol": mql5_symbol,
                "mql5_timeframe": mql5_timeframe,
                "timeframe": mql5_timeframe,
                "status": "WITHHELD",
                "reason": "SQX_PAIR_MISSING",
            }
        )
    magic_counts = defaultdict(int)
    for item in items:
        if item["status"] == "STATIC_VALIDATED" and item["magic_number"] is not None:
            magic_counts[int(item["magic_number"])] += 1
    for item in items:
        if (
            item["status"] == "STATIC_VALIDATED"
            and item["magic_number"] is not None
            and magic_counts[int(item["magic_number"])] > 1
        ):
            item["status"] = "WITHHELD"
            item["reason"] = "DUPLICATE_MAGIC_NUMBER"
    return items


async def persist(items: list[dict[str, object]]) -> None:
    from core.config import get_settings
    from core.db.base import async_session_factory
    from core.db.enums import AssetAdmissionStatus, AssetSourceGroup
    from core.db.models.operations import OperationalAsset, OperationalAssetEvent
    from sqlalchemy import select

    if get_settings().deployment_profile != "operational":
        raise RuntimeError("--apply exige DEPLOYMENT_PROFILE=operational")
    async with async_session_factory() as session:
        for item in items:
            existing = (
                await session.execute(
                    select(OperationalAsset).where(
                        OperationalAsset.sqx_sha256 == item["sqx_sha256"],
                        OperationalAsset.mql5_sha256 == item["mql5_sha256"],
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue
            asset = OperationalAsset(
                source_group=AssetSourceGroup(str(item["source_group"])),
                source_root=str(item["source_root"]),
                sqx_path=item["sqx_path"],
                mql5_path=item["mql5_path"],
                sqx_sha256=item["sqx_sha256"],
                mql5_sha256=item["mql5_sha256"],
                strategy_name=item["strategy_name"],
                magic_number=item["magic_number"],
                symbol=item.get("symbol"),
                timeframe=item["timeframe"],
                discovered_at=datetime.now(UTC),
            )
            session.add(asset)
            await session.flush()
            session.add(
                OperationalAssetEvent(
                    asset_id=asset.id,
                    status=AssetAdmissionStatus(str(item["status"])),
                    reason=item["reason"],
                    evidence={"manifest": "operational_inventory_v1"},
                    occurred_at=datetime.now(UTC),
                )
            )
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument(
        "--source-root",
        help="ruta de procedencia que se persiste; útil cuando --root es un montaje read-only",
    )
    parser.add_argument("--source-group", choices=("REAL", "INCUBATOR", "ANALYSIS"), required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--apply-existing-manifest",
        action="store_true",
        help="persiste un manifiesto previamente generado en el host sin reexaminar fuentes",
    )
    args = parser.parse_args()
    if args.apply_existing_manifest:
        if not args.apply:
            raise SystemExit("--apply-existing-manifest exige --apply")
        try:
            stored = json.loads(args.manifest.read_text(encoding="utf-8"))
            items = stored["items"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SystemExit(f"manifiesto de inventario inválido: {exc}") from exc
        if not isinstance(items, list):
            raise SystemExit("manifiesto de inventario sin items")
        print(f"inventory={len(items)} manifest={args.manifest} mode=apply-existing")
    else:
        if args.root is None or not args.root.is_dir():
            raise SystemExit(f"root inexistente: {args.root}")
        items = build_inventory(args.root, args.source_group, source_root=args.source_root)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(
                {"generated_at_utc": datetime.now(UTC).isoformat(), "items": items},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"inventory={len(items)} manifest={args.manifest}")
    if args.apply:
        asyncio.run(persist(items))


if __name__ == "__main__":
    main()
