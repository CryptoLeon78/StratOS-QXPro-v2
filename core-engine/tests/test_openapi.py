"""PARTE 12/G5, criterio de salida literal: "OpenAPI sin warnings". Sin un
validador de spec como dependencia nueva (ninguno de los 16 routers lo
necesitaba hasta ahora): se comprueba lo que realmente puede fallar en
`app.openapi()` -- warnings de Python durante la generacion (Pydantic/
FastAPI avisan de esquemas ambiguos o `operationId` duplicados con un
`UserWarning`, nunca con una excepcion) mas dos invariantes estructurales
que FastAPI no garantiza solo: operationId unico por operacion y tags no
vacios (una operacion sin tag aparece suelta en la raiz de Swagger UI,
fuera de los 16 dominios agrupados de PARTE 9.2)."""

import warnings

from core.main import app


def _generate_schema() -> tuple[dict[str, object], list[warnings.WarningMessage]]:
    app.openapi_schema = None  # fuerza regeneracion, ignora la cache de FastAPI
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        schema = app.openapi()
    return schema, caught


def test_openapi_generation_emits_no_warnings() -> None:
    _schema, caught = _generate_schema()
    assert caught == []


def test_every_operation_has_a_unique_operation_id() -> None:
    schema, _ = _generate_schema()
    seen: dict[str, tuple[str, str]] = {}
    for path, methods in schema["paths"].items():  # type: ignore[attr-defined]
        for method, operation in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            operation_id = operation["operationId"]
            assert operation_id not in seen, (
                f"operationId duplicado {operation_id!r}: {seen[operation_id]} vs {(path, method)}"
            )
            seen[operation_id] = (path, method)


def test_every_operation_has_at_least_one_tag() -> None:
    schema, _ = _generate_schema()
    untagged: list[tuple[str, str]] = []
    for path, methods in schema["paths"].items():  # type: ignore[attr-defined]
        for method, operation in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            if not operation.get("tags"):
                untagged.append((path, method))
    assert untagged == []
