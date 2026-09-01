"""Importador local administrativo de CSV FX con procedencia y sello."""

import argparse
import asyncio
from pathlib import Path

from core.db.base import async_session_factory
from core.services.admin_imports import import_fx_csv


async def run(path: Path) -> None:
    async with async_session_factory() as session:
        inserted = await import_fx_csv(session, path=path)
        await session.commit()
    print(f"fx_rows_inserted={inserted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    asyncio.run(run(parser.parse_args().csv))
