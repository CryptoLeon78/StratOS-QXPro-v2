"""Registra una observación inmutable de EA real, sin tocar MT5 ni dar F7."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path

import core.db.models  # noqa: F401
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.models.accounts import Account, Bot
from core.db.models.operations import ExternalEaInventory
from sqlalchemy import select


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--ea-file", required=True, type=Path)
    parser.add_argument("--ea-relative-path", required=True)
    parser.add_argument("--comment-identity", required=True)
    parser.add_argument("--magic", type=int)
    parser.add_argument("--symbol")
    parser.add_argument("--timeframe")
    parser.add_argument("--bot-id", type=int)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def record(args: argparse.Namespace) -> str:
    if get_settings().deployment_profile != "operational":
        raise RuntimeError("inventario externo permitido sólo en DEPLOYMENT_PROFILE=operational")
    if not args.ea_file.is_file() or not args.comment_identity.strip():
        raise ValueError("EA y comment_identity son obligatorios")
    digest = hashlib.sha256(args.ea_file.read_bytes()).hexdigest()
    if not args.apply:
        return f"planned account={args.account_login} file={args.ea_file.name} sha256={digest} magic={args.magic}"
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == args.account_login))
        if account is None:
            raise ValueError("cuenta no registrada")
        bot = await session.get(Bot, args.bot_id) if args.bot_id is not None else None
        if bot is not None and (bot.account_id != account.id or bot.magic_number != args.magic):
            raise ValueError("bot_id no coincide con cuenta y magic observados")
        row = ExternalEaInventory(account_id=account.id, bot_id=args.bot_id, ea_filename=args.ea_file.name,
            ea_relative_path=args.ea_relative_path, ea_sha256=digest, comment_identity=args.comment_identity,
            magic_number=args.magic, symbol=args.symbol, timeframe=args.timeframe, observed_at=datetime.now(UTC))
        session.add(row)
        await session.commit()
    return f"inventory_id={row.id} magic={args.magic} bot_id={args.bot_id} sha256={digest}"


def main() -> None:
    try:
        print(asyncio.run(record(parse_args())))
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"BLOQUEADO: {exc}") from exc


if __name__ == "__main__":
    main()
