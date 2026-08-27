"""Usuario de login para el harness Playwright (G6 `resumen.spec.ts` ya
documentaba en su ASSUMPTIONS G6-03 que se verificaba "con un usuario de
dev creado a mano (nunca commiteado)" -- G8 es la fase que cierra ese
hueco: si `PLAYWRIGHT_TEST_EMAIL`/`PLAYWRIGHT_TEST_PASSWORD` estan en el
entorno (nunca hardcodeadas aqui ni en ningun spec), se crea/actualiza un
`User` real con la contraseña hasheada (`auth/security.py::hash_password`,
argon2, el mismo que usa el login real) para que el propio job de CI
pueda loguearse contra lo que acaba de sembrar. Sin esas 2 variables, es
un no-op silencioso -- no bloquea `seed.py` para quien solo quiere datos,
sin credenciales de prueba."""

import os
from datetime import datetime

from core.auth.security import hash_password
from core.db.models.governance import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_test_user(session: AsyncSession, now: datetime) -> User | None:
    email = os.environ.get("PLAYWRIGHT_TEST_EMAIL")
    password = os.environ.get("PLAYWRIGHT_TEST_PASSWORD")
    if not email or not password:
        return None

    existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        existing.hashed_password = hash_password(password)
        return existing

    user = User(
        email=email, hashed_password=hash_password(password), role="operator", created_at=now
    )
    session.add(user)
    await session.flush()
    return user
