"""Un lote con un sello ya visto se sella igual, pero no se reprocesa.

El sello SHA-256 cubre `(account_login, batch_type, records)`: si coincide con
uno ya registrado, el lote es byte a byte el mismo y no hay nada que ingerir.
La ingesta ya era idempotente (P9, `ON CONFLICT`), asi que reprocesarlo no
cambiaba ningun dato -- solo costaba el trabajo.

Y costaba mucho. El 2026-09-26 el conector reenviaba su historico completo en
cada ciclo: **141 lotes y 317.670 registros en 20 minutos** para cero filas
nuevas, con 102.034 lotes de trades acumulados. Cada reenvio hacia ~2.253
upserts que colisionaban con filas existentes, y la contencion resultante
dejaba el login en 7-17 s.

El servidor no puede depender de que el cliente se porte bien: detectar el
sello repetido es defensa propia, no una optimizacion.
"""

from __future__ import annotations

import pytest

from core.ingest import batch as batch_module


class _SesionFalsa:
    def __init__(self, sello_existente: str | None) -> None:
        self._existente = sello_existente
        self.anadidos: list[object] = []

    async def execute(self, *args: object, **kwargs: object) -> object:
        existente = self._existente

        class Resultado:
            def scalar_one_or_none(self) -> object | None:
                return object() if existente else None

        return Resultado()

    def add(self, obj: object) -> None:
        self.anadidos.append(obj)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_un_sello_ya_registrado_se_marca_como_ya_visto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(batch_module, "verify_batch_seal", lambda *a, **k: None)
    session = _SesionFalsa(sello_existente="abc")
    cuenta = type("Cuenta", (), {"id": 1})()

    resultado = await batch_module.seal_and_create_batch(
        session,  # type: ignore[arg-type]
        cuenta,  # type: ignore[arg-type]
        "trades",
        "LOGIN",
        "conn-1",
        "abc",
        [{"x": 1}],
        2253,
    )

    lote, ya_visto = resultado
    assert ya_visto is True, "avisa de que ese sello ya estaba registrado"
    assert lote is not None
    # La traza no se toca: cada intento sella su propia fila (append-only real),
    # que es justo lo que deja ver que un conector esta reenviando.
    assert len(session.anadidos) == 1


@pytest.mark.asyncio
async def test_un_sello_nuevo_sigue_registrandose(monkeypatch: pytest.MonkeyPatch) -> None:
    """La deduplicacion no puede tragarse un lote legitimo."""
    monkeypatch.setattr(batch_module, "verify_batch_seal", lambda *a, **k: None)
    session = _SesionFalsa(sello_existente=None)
    cuenta = type("Cuenta", (), {"id": 1})()

    resultado = await batch_module.seal_and_create_batch(
        session,  # type: ignore[arg-type]
        cuenta,  # type: ignore[arg-type]
        "trades",
        "LOGIN",
        "conn-1",
        "nuevo",
        [{"x": 1}],
        10,
    )

    lote, ya_visto = resultado
    assert ya_visto is False
    assert lote is not None
    assert len(session.anadidos) == 1
