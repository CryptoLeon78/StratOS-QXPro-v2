"""Backfill de atribución sobre trades históricos ya cerrados.

Sin BD real (no hay fixture de sesión a nivel de `scripts/tests`, igual que
`test_import_mt5_history_export.py`): la sesión se falsea para que
`session.execute(...)` devuelva las filas de prueba, y `_resolve_bot_id` se
sustituye directamente -- su propia lógica ya la cubre
`core-engine/tests/ingest`. Lo que este test verifica es la decisión de
ESTE script: qué trades toca, cuáles retiene y qué reporta.
"""

from __future__ import annotations

import pytest

import backfill_legacy_magic_attribution as modulo
from backfill_legacy_magic_attribution import backfill_legacy_magic_attribution


class _TradeFalso:
    def __init__(self, magic_number: int, bot_id: int | None = None) -> None:
        self.magic_number = magic_number
        self.bot_id = bot_id


class _ResultadoFalso:
    def __init__(self, trades: list[_TradeFalso]) -> None:
        self._trades = trades

    def scalars(self) -> _ResultadoFalso:
        return self

    def all(self) -> list[_TradeFalso]:
        return self._trades


class _SesionFalsa:
    def __init__(self, trades: list[_TradeFalso]) -> None:
        self._trades = trades
        self.committed = False
        self.rolled_back = False

    async def execute(self, *args: object, **kwargs: object) -> _ResultadoFalso:
        return _ResultadoFalso(self._trades)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


MAPA = {7786: {"magic_number": 1, "comment_identity": "XAUH1BUYSTOPeof_1.8.81_MN1"}}


def _resolver_a(bot_id: int | None):
    async def _resolver(session: object, account_id: int, magic_number: int) -> int | None:
        assert magic_number == 1
        return bot_id

    return _resolver


@pytest.mark.asyncio
async def test_traduce_y_atribuye_una_fila_huerfana(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo, "_resolve_bot_id", _resolver_a(42))
    trade = _TradeFalso(magic_number=7786, bot_id=None)
    session = _SesionFalsa([trade])

    report = await backfill_legacy_magic_attribution(
        session, account_id=1, legacy_magic_map=MAPA, apply=True
    )

    assert report.total_newly_attributed == 1
    assert report.total_stale_magic_fixed == 0
    assert report.total_conflicts == 0
    assert trade.magic_number == 1, "se traduce al magic vigente"
    assert trade.bot_id == 42, "se resuelve el bot con el magic ya traducido"
    assert session.committed is True


@pytest.mark.asyncio
async def test_dry_run_no_escribe_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo, "_resolve_bot_id", _resolver_a(42))
    trade = _TradeFalso(magic_number=7786, bot_id=None)
    session = _SesionFalsa([trade])

    report = await backfill_legacy_magic_attribution(
        session, account_id=1, legacy_magic_map=MAPA, apply=False
    )

    assert report.total_translated == 1, "el reporte cuenta igual en dry-run"
    assert trade.magic_number == 7786, "sin --apply no se toca el objeto"
    assert trade.bot_id is None
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_traduce_sin_bot_registrado_todavia_queda_huerfana_bajo_el_nuevo_magic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Traducir el magic no es lo mismo que atribuir: si aun no hay Bot con el
    magic vigente, la fila se corrige igual (para no repetir la traduccion en
    cada corrida) pero sigue huerfana, declarada como tal en el reporte."""
    monkeypatch.setattr(modulo, "_resolve_bot_id", _resolver_a(None))
    trade = _TradeFalso(magic_number=7786, bot_id=None)
    session = _SesionFalsa([trade])

    report = await backfill_legacy_magic_attribution(
        session, account_id=1, legacy_magic_map=MAPA, apply=True
    )

    assert report.total_newly_attributed == 1
    assert trade.magic_number == 1
    assert trade.bot_id is None


@pytest.mark.asyncio
async def test_una_fila_ya_atribuida_al_bot_correcto_solo_corrige_el_campo_obsoleto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso real medido contra el stack (184 trades BEPB, 2026-09-26):
    `scripts/sync_bot_magics_to_migration.py` ya corrigio el magic del Bot
    de legacy a vigente, asi que el trade atribuido ANTES de esa
    sincronizacion conserva su bot_id correcto pero su propio
    magic_number sigue siendo el valor viejo. Aqui es seguro corregir
    solo el campo: bot_id no cambia porque ya era el correcto."""
    monkeypatch.setattr(modulo, "_resolve_bot_id", _resolver_a(99))
    trade = _TradeFalso(magic_number=7786, bot_id=99)
    session = _SesionFalsa([trade])

    report = await backfill_legacy_magic_attribution(
        session, account_id=1, legacy_magic_map=MAPA, apply=True
    )

    assert report.total_stale_magic_fixed == 1
    assert report.total_newly_attributed == 0
    assert report.total_conflicts == 0
    assert trade.magic_number == 1, "se corrige el campo obsoleto"
    assert trade.bot_id == 99, "bot_id no cambia: ya era el correcto"


@pytest.mark.asyncio
async def test_una_fila_atribuida_a_otro_bot_distinto_se_retiene_como_conflicto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La anomalia real: bot_id ya asignado, pero a un bot DISTINTO de donde
    traduciria el magic legacy (o a ninguno, si la traduccion no resuelve).
    Ahi si hay algo que no cuadra -- por ejemplo un EA que sigue emitiendo
    su magic legacy de verdad -- y no se toca."""
    monkeypatch.setattr(modulo, "_resolve_bot_id", _resolver_a(1))
    trade = _TradeFalso(magic_number=7786, bot_id=99)
    session = _SesionFalsa([trade])

    report = await backfill_legacy_magic_attribution(
        session, account_id=1, legacy_magic_map=MAPA, apply=True
    )

    assert report.total_translated == 0
    assert report.total_conflicts == 1
    assert trade.magic_number == 7786, "no se toca"
    assert trade.bot_id == 99, "no se toca"


@pytest.mark.asyncio
async def test_una_segunda_corrida_no_encuentra_nada_que_traducir() -> None:
    """Idempotencia real: tras aplicar, el trade ya no lleva el magic legacy,
    asi que una corrida repetida contra la BD real ni siquiera lo seleccionaria
    (el WHERE filtra por magic_number.in_(legacy_map)). Aqui se simula ese
    estado posterior con la lista de filas ya vacia."""
    session = _SesionFalsa([])

    report = await backfill_legacy_magic_attribution(
        session, account_id=1, legacy_magic_map=MAPA, apply=True
    )

    assert report.total_translated == 0
    assert report.total_conflicts == 0


@pytest.mark.asyncio
async def test_sin_registro_de_identidad_no_hace_nada() -> None:
    session = _SesionFalsa([_TradeFalso(magic_number=7786)])

    report = await backfill_legacy_magic_attribution(
        session, account_id=1, legacy_magic_map={}, apply=True
    )

    assert report.total_translated == 0
