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
