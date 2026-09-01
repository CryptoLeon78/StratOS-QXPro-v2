"""Crea o rota el acceso del operador sólo dentro de la base aislada G12."""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import UTC, datetime

from sqlalchemy import select

from core.auth.security import hash_password
from core.db.base import async_session_factory
from core.db.models.governance import User


def _assert_g12_database(database_url: str) -> None:
    if "/stratos_g12" not in database_url:
        raise ValueError("alta bloqueada: DATABASE_URL no apunta a stratos_g12")


# Politica local de la campana: la contrasena se entrega una sola vez al operador fuera
# del repositorio, asi que su longitud minima se comprueba aqui y no en SystemConfig,
# que esta en la base que este mismo script inicializa.
MIN_OPERATOR_PASSWORD_LENGTH = 16


async def create_or_rotate_operator(email: str, password: str) -> str:
    _assert_g12_database(os.environ.get("DATABASE_URL", ""))
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("email de operador inválido")
    if len(password) < MIN_OPERATOR_PASSWORD_LENGTH:
        raise ValueError(
            f"contraseña G12 demasiado corta: mínimo {MIN_OPERATOR_PASSWORD_LENGTH} caracteres"
        )
    async with async_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            session.add(
                User(
                    email=normalized_email,
                    hashed_password=hash_password(password),
                    role="operator",
                    created_at=datetime.now(UTC),
                )
            )
            result = "creado"
        else:
            user.hashed_password = hash_password(password)
            result = "rotado"
        await session.commit()
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password-env", required=True)
    parser.add_argument("--confirm-g12", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.confirm_g12:
        raise SystemExit("alta no aplicada: añade --confirm-g12")
    password = os.environ.get(args.password_env)
    if not password:
        raise SystemExit(f"no existe la variable de contraseña {args.password_env!r}")
    result = asyncio.run(create_or_rotate_operator(args.email, password))
    print(f"Operador G12 {result}: {args.email.strip().lower()}")


if __name__ == "__main__":
    main()
