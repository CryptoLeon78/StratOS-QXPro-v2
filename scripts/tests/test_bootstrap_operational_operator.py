from asyncio import run
from types import SimpleNamespace

import pytest

import bootstrap_operational_operator


def test_bootstrap_operator_rejects_non_operational_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap_operational_operator,
        "get_settings",
        lambda: SimpleNamespace(deployment_profile="full"),
    )

    with pytest.raises(SystemExit, match="DEPLOYMENT_PROFILE=operational"):
        run(bootstrap_operational_operator.bootstrap())


def test_bootstrap_operator_rechaza_una_contrasena_sin_hashear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El valor se guarda tal cual en `hashed_password`, así que debe ser un hash.

    Aceptar texto plano crea un operador que no puede entrar nunca: Argon2 lanza
    `InvalidHashError` al verificar y el login devuelve False sin decir por qué.
    Fallar aquí, en el alta, es la única forma de que el error sea legible.
    """
    monkeypatch.setattr(
        bootstrap_operational_operator,
        "get_settings",
        lambda: SimpleNamespace(
            deployment_profile="operational",
            operator_email="operador@ejemplo.com",
            operator_password_hash="unaContrasena",
        ),
    )

    with pytest.raises(SystemExit, match="no es un hash Argon2"):
        run(bootstrap_operational_operator.bootstrap())


def test_bootstrap_operator_detecta_los_dolares_duplicados_de_compose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`$$argon2id$$...` es un hash escapado para docker compose, no un hash.

    El mismo `.env.operational` se pasa como `--env-file` (donde compose
    interpola `$`) y como `env_file:` del servicio (donde llega literal).
    Escapar los `$` para silenciar el warning de compose rompe el valor que
    recibe la aplicacion, y el sintoma es un login que falla sin explicacion.
    Se nombra el caso porque el mensaje generico mandaria a regenerar un hash
    que ya era correcto.
    """
    monkeypatch.setattr(
        bootstrap_operational_operator,
        "get_settings",
        lambda: SimpleNamespace(
            deployment_profile="operational",
            operator_email="operador@ejemplo.com",
            operator_password_hash="$$argon2id$$v=19$$m=65536,t=3,p=4$$sal$$hash",
        ),
    )

    with pytest.raises(SystemExit, match="dolares duplicados"):
        run(bootstrap_operational_operator.bootstrap())
