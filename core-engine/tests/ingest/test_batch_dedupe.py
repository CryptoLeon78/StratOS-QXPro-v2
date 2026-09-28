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

import hashlib

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.decisions import Alert
from core.ingest import batch as batch_module
from tests.factories import AccountFactory, IngestBatchFactory


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


async def test_un_sello_reenviado_dos_veces_no_revienta_al_tercer_intento(
    db_session: AsyncSession,
) -> None:
    """Bug real en produccion, 2026-09-28: por diseno de esta misma funcion
    (docstring de arriba), cada reenvio del mismo lote deja SU PROPIA fila --
    tras el segundo reenvio ya hay 2 filas con el mismo (account_id,
    batch_type, sha256). Sin `.limit(1)` en la consulta de idempotencia, un
    TERCER reenvio legitimo (exactamente el escenario "141 reenvios en 20
    minutos" que motivo esta funcion) hacia que `.scalar_one_or_none()`
    lanzara `MultipleResultsFound` -- 500 real en /ingest/equity y
    /ingest/positions contra las cuentas reales JJTI/BEPB. El test anterior
    de este fichero mockea `scalar_one_or_none()` directamente y nunca
    ejercita el comportamiento real de SQLAlchemy con 2+ filas -- por eso no
    lo detecto. Este usa una BD real."""
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()

    seal = hashlib.sha256(b"lote-reenviado-3-veces").hexdigest()
    # Simula que la funcion ya se llamo 2 veces antes con este mismo sello:
    # 2 filas ya existen para (account_id, batch_type, sha256).
    db_session.add(IngestBatchFactory(account_id=account.id, batch_type="equity", sha256=seal))
    db_session.add(IngestBatchFactory(account_id=account.id, batch_type="equity", sha256=seal))
    await db_session.flush()

    monkeypatch_target = batch_module.verify_batch_seal
    batch_module.verify_batch_seal = lambda *a, **k: None  # type: ignore[assignment]
    try:
        lote, ya_visto = await batch_module.seal_and_create_batch(
            db_session,
            account,
            "equity",
            "LOGIN",
            "conn-1",
            seal,
            [{"x": 1}],
            10,
        )
    finally:
        batch_module.verify_batch_seal = monkeypatch_target

    assert ya_visto is True, "el sello ya estaba registrado (2 veces); debe avisar, no reventar"
    assert lote is not None


async def _reenviar(db_session: AsyncSession, account: object, seal: str, n: int) -> None:
    """Simula `n` reenvios reales del mismo sello, uno a uno (no bulk-insert
    directo): cada llamada pasa por `_alert_if_excessive_resend`, igual que
    en produccion."""
    monkeypatch_target = batch_module.verify_batch_seal
    batch_module.verify_batch_seal = lambda *a, **k: None  # type: ignore[assignment]
    try:
        for _ in range(n):
            await batch_module.seal_and_create_batch(
                db_session,
                account,
                "trades",
                "LOGIN",
                "conn-1",
                seal,
                [{"x": 1}],
                10,  # type: ignore[arg-type]
            )
    finally:
        batch_module.verify_batch_seal = monkeypatch_target


async def test_pocos_reenvios_no_generan_alerta(db_session: AsyncSession) -> None:
    """El escenario de diseno original ("141 reenvios en 20 minutos") es
    ruido tolerado, no una alerta -- el umbral debe quedar por debajo de
    ese volumen real sin disparar en el caso normal."""
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()
    seal = hashlib.sha256(b"pocos-reenvios").hexdigest()

    await _reenviar(db_session, account, seal, batch_module._EXCESSIVE_RESEND_ALERT_THRESHOLD - 1)

    n_alerts = (
        await db_session.execute(
            select(func.count()).select_from(Alert).where(Alert.module == "ingest_batch")
        )
    ).scalar_one()
    assert n_alerts == 0


async def test_reenvios_excesivos_generan_una_sola_alerta(db_session: AsyncSession) -> None:
    """G13-75: un conector atascado reenviando el mismo sello debe quedar
    visible en Auditoria en vez de acumular filas en silencio durante
    semanas (caso real: 52.512 filas de BEPB, 21 dias, cero alertas). Una
    sola alerta por sello (dedup_key), no una por cada reenvio posterior al
    umbral -- de lo contrario un conector atascado seguiria generando ruido
    sin parar en vez de una senal unica y accionable."""
    account = AccountFactory()
    db_session.add(account)
    await db_session.flush()
    seal = hashlib.sha256(b"conector-atascado").hexdigest()

    await _reenviar(db_session, account, seal, batch_module._EXCESSIVE_RESEND_ALERT_THRESHOLD)
    await _reenviar(db_session, account, seal, 5)  # sigue reenviando tras la alerta

    alerts = (
        (await db_session.execute(select(Alert).where(Alert.module == "ingest_batch")))
        .scalars()
        .all()
    )
    assert len(alerts) == 1
    assert alerts[0].dedup_key == batch_module._excessive_resend_dedup_key(
        account.id, "trades", seal
    )
    assert alerts[0].resolved is False
    assert str(account.id) in alerts[0].message
    assert "trades" in alerts[0].message
