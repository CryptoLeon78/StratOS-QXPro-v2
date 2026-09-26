"""Rota o actualiza la contraseña del operador en el stack operacional.

Uso interactivo (pide contraseña de forma segura sin mostrarla en pantalla):
  .venv\\Scripts\\python.exe scripts/rotate_operational_operator_password.py --email ivanaza8@gmail.com

Uso no interactivo mediante variable de entorno:
  $env:NUEVA_PASS="mi_password_seguro"
  .venv\\Scripts\\python.exe scripts/rotate_operational_operator_password.py --email ivanaza8@gmail.com --password-env NUEVA_PASS
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from core.auth.security import hash_password
from core.db.base import async_session_factory
from core.db.models.governance import User

MIN_OPERATOR_PASSWORD_LENGTH = 12


async def update_operator_password(email: str, password: str) -> str:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("email de operador inválido")
    if len(password) < MIN_OPERATOR_PASSWORD_LENGTH:
        raise ValueError(
            f"contraseña demasiado corta: mínimo {MIN_OPERATOR_PASSWORD_LENGTH} caracteres"
        )
    async with async_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            user = User(
                email=normalized_email,
                hashed_password=hash_password(password),
                role="operator",
                created_at=datetime.now(UTC),
            )
            session.add(user)
            result = "creado"
        else:
            user.hashed_password = hash_password(password)
            result = "actualizado"
        await session.commit()
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", help="Email del operador (ej. ivanaza8@gmail.com)")
    parser.add_argument(
        "--password-env",
        help="Nombre de la variable de entorno que contiene la nueva contraseña",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    email = args.email
    if not email:
        email = input("Introduce el email del operador: ").strip()

    if args.password_env:
        password = os.environ.get(args.password_env, "")
        if not password:
            raise SystemExit(f"La variable de entorno {args.password_env!r} está vacía o no existe.")
    else:
        password = getpass.getpass("Introduce la nueva contraseña (mínimo 12 caracteres): ")
        password_confirm = getpass.getpass("Confirma la nueva contraseña: ")
        if password != password_confirm:
            raise SystemExit("Error: Las contraseñas no coinciden.")

    if len(password) < MIN_OPERATOR_PASSWORD_LENGTH:
        raise SystemExit(
            f"Error: La contraseña debe tener al menos {MIN_OPERATOR_PASSWORD_LENGTH} caracteres."
        )

    result = asyncio.run(update_operator_password(email, password))
    print(f"Operador {email} {result} con éxito en la base de datos.")


if __name__ == "__main__":
    main()
