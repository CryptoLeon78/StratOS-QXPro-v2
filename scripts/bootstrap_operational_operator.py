"""Crea el operador inicial únicamente en el stack operacional aislado.

La contraseña ya debe estar hasheada en ``OPERATOR_PASSWORD_HASH`` de la
configuración local. El script nunca muestra email, hash ni secretos y no
rota un operador existente.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from core.config import get_settings
from core.db.base import async_session_factory
from core.db.models.governance import User

# El valor se guarda tal cual en `hashed_password`, y el login lo verifica con
# Argon2. Un texto plano crea un operador que no puede entrar nunca: Argon2
# lanza InvalidHashError y `verify_password` devuelve False sin decir por qué.
ARGON2_PREFIX = "$argon2"


async def bootstrap() -> str:
    settings = get_settings()
    if settings.deployment_profile != "operational":
        raise SystemExit("alta de operador permitida sólo en DEPLOYMENT_PROFILE=operational")
    email = settings.operator_email.strip().lower()
    password_hash = settings.operator_password_hash.strip()
    if not email or "@" not in email or not password_hash:
        raise SystemExit("faltan OPERATOR_EMAIL u OPERATOR_PASSWORD_HASH locales válidos")
    if not password_hash.startswith(ARGON2_PREFIX):
        raise SystemExit(
            "OPERATOR_PASSWORD_HASH no es un hash Argon2. Genéralo con:\n"
            '  python -c "from argon2 import PasswordHasher; '
            'print(PasswordHasher().hash(input()))"'
        )
    async with async_session_factory() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            return "operator_exists"
        session.add(
            User(
                email=email,
                hashed_password=password_hash,
                role="operator",
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()
    return "operator_created"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("alta no aplicada: añade --apply")
    print(asyncio.run(bootstrap()))


if __name__ == "__main__":
    main()
