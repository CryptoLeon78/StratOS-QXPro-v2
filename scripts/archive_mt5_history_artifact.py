"""Sella en StratOS un export MT5 que todavía no cumple el contrato de trades.

Los formatos heredados se preservan como evidencia inmutable, pero no generan
trades ni asociaciones por heurística. El importador canónico sigue siendo
import_mt5_history_export.py para CSV con position_id y entradas/salidas.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from core.config import get_settings
from core.db.base import async_session_factory
from core.services.admin_imports import _artifact_metadata, _get_or_create_artifact


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--source-terminal", required=True)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--format", required=True, choices=("MT5_DETAILED_LEGACY", "MT5_SUMMARY_LEGACY"))
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def archive(args: argparse.Namespace) -> str:
    if get_settings().deployment_profile != "operational":
        raise RuntimeError("archivo histórico permitido sólo en DEPLOYMENT_PROFILE=operational")
    payload = args.file.read_bytes()
    if not payload:
        raise ValueError("artefacto histórico vacío")
    if not args.apply:
        return f"planned file={args.file} format={args.format}"
    async with async_session_factory() as session:
        artifact = await _get_or_create_artifact(
            session,
            kind=args.format,
            path=args.file,
            payload=payload,
            parser_version="mt5-legacy-history-v1",
            metadata=_artifact_metadata(
                args.file,
                account_login=args.account_login,
                source_terminal=args.source_terminal,
                window_start=args.window_start,
                window_end=args.window_end,
                trade_imported=False,
                withholding_reason="LEGACY_FORMAT_NO_POSITION_ID_OR_DEAL_ENTRY",
            ),
        )
        await session.commit()
    return f"archived artifact_id={artifact.id} sha256={artifact.sha256} trades_imported=false"


def main() -> None:
    try:
        print(asyncio.run(archive(parse_args())))
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"BLOQUEADO: {exc}") from exc


if __name__ == "__main__":
    main()
