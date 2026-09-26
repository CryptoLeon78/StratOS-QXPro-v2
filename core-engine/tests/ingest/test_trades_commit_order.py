"""La ingesta confirma antes de evaluar el pipeline.

`post_trades` hacia el upsert y **despues** evaluaba F5 y F6, todo dentro de
la misma transaccion: los locks de las filas de `trade` se retenian durante
toda la evaluacion. Con el conector reintentando lotes solapados de las mismas
cuentas, cada intento esperaba al anterior y el pool acababa lleno de
conexiones bloqueadas -- el 2026-09-26, 34 de 35 en `Lock/tuple`, con `trade`
parado 19 dias.

El criterio ya estaba escrito en este mismo router, en `post_positions`: el
trabajo que no es la ingesta va **despues** del commit, porque un fallo suyo
no debe arriesgar un rollback de dominio. El trade es dato primario e
idempotente; la evaluacion es derivada y se repite en el siguiente lote.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.ingest import router as ingest_router


@pytest.mark.asyncio
async def test_los_trades_se_confirman_antes_de_evaluar_el_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orden: list[str] = []

    class SesionFalsa:
        async def commit(self) -> None:
            orden.append("commit")

        async def flush(self) -> None:
            orden.append("flush")

    class ResultadoFalso:
        def _asdict(self) -> dict[str, object]:
            return {
                "accepted": 1,
                "duplicated": 0,
                "batch_id": 1,
                "server_time": datetime.now(UTC),
            }

    async def fake_resolve(session: object, login: str) -> object:
        return type("Cuenta", (), {"id": 1})()

    async def fake_ingest(*args: object, **kwargs: object) -> ResultadoFalso:
        orden.append("upsert")
        return ResultadoFalso()

    async def fake_f5(*args: object, **kwargs: object) -> None:
        orden.append("f5")

    async def fake_f6(*args: object, **kwargs: object) -> None:
        orden.append("f6")

    monkeypatch.setattr(ingest_router, "resolve_account", fake_resolve)
    monkeypatch.setattr(ingest_router, "ingest_trades", fake_ingest)
    monkeypatch.setattr(ingest_router, "evaluate_f5_candidates_for_account", fake_f5)
    monkeypatch.setattr(ingest_router, "evaluate_f6_candidates_for_account", fake_f6)

    req = type("Req", (), {"account_login": "X"})()
    await ingest_router.post_trades(req, session=SesionFalsa(), redis=object())  # type: ignore[arg-type]

    assert "commit" in orden, "la ingesta debe confirmar"
    assert orden.index("upsert") < orden.index("commit"), "se confirma despues del upsert"
    for evaluacion in ("f5", "f6"):
        assert orden.index("commit") < orden.index(evaluacion), (
            f"{evaluacion} debe evaluarse DESPUES del commit para no retener los locks; "
            f"orden observado: {orden}"
        )
