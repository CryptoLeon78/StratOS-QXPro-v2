"""Importador local administrativo de una baseline SQX144, sin ruta HTTP."""

import argparse
import asyncio
from decimal import Decimal
from pathlib import Path

from core.db.base import async_session_factory
from core.services.admin_imports import import_sqx_baseline


async def run(args: argparse.Namespace) -> None:
    async with async_session_factory() as session:
        baseline = await import_sqx_baseline(
            session, bot_id=args.bot_id, path=args.sqx, dd_contract_pct=args.dd_contract_pct
        )
        await session.commit()
    print(f"baseline_id={baseline.id} bot_id={args.bot_id} source=SQX144")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bot-id", required=True, type=int)
    parser.add_argument("--sqx", required=True, type=Path)
    parser.add_argument("--dd-contract-pct", required=True, type=Decimal)
    asyncio.run(run(parser.parse_args()))
