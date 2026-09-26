"""Los `docs/registro_*_MN_*.md` describen el estado **posterior** a la migracion de
identidad compacta (ASSUMPTIONS G13-18/G13-20): magics nuevos y `CustomComment` con el
sufijo `_MN<magic>`. La observacion **anterior** a la migracion vive, inmutable, en los
manifiestos sellados de `runtime/operational/external_inventory/`.

Cada propiedad se verifica contra la fuente que de verdad la afirma. Mezclarlas fue lo que
dejo este modulo en rojo: un test comprobaba la colision `magic=10827` (un hecho
pre-migracion) leyendo el documento post-migracion, donde esa colision ya no existe porque
la propia migracion la resolvio.
"""

import json
from pathlib import Path

from import_external_ea_inventory_records import parse_records


ROOT = Path(__file__).resolve().parents[2]
SEALED_INVENTORY = ROOT / "runtime" / "operational" / "external_inventory"

# Colision observada en BEPB antes de la migracion: dos EAs GDAXI H1 distintos compartiendo
# magic. La migracion la resolvio moviendo `5.29.24` a 10829 (ver test de abajo).
PRE_MIGRATION_COLLIDING_MAGIC = 10827


def test_parses_operator_bepb_magic_records() -> None:
    """Tras el A13/A16 (2026-09-26, `scripts/regenerate_mn_registry_docs.py`), el primer
    registro carga el magic *vigente* 28 -- traducido desde el legacy 7507 -- porque el
    documento ya no se mantiene a mano con el magic anterior a la migracion."""
    records = parse_records(ROOT / "docs" / "registro_BEPB_MN_bots_real_mt5_vps.md", "BEPB")
    assert len(records) == 32
    assert records[0].magic_number == 28


def test_parses_operator_jjti_magic_records() -> None:
    """Ver nota de `test_parses_operator_bepb_magic_records`: el ultimo registro carga el
    magic vigente 25, traducido desde el legacy 200735."""
    records = parse_records(ROOT / "docs" / "registro_JJTI_MN_bots_real_mt5_vps.md", "JJTI")
    assert len(records) == 24
    assert records[0].comment_identity == "EURUSDM15S_3.76.81_MN301"
    assert records[-1].magic_number == 25


def test_post_migration_registries_have_unique_magics() -> None:
    """El objetivo de la migracion: un magic identifica a un solo EA dentro de su cuenta."""
    for archivo, cuenta, esperados in [
        ("registro_BEPB_MN_bots_real_mt5_vps.md", "BEPB", 32),
        ("registro_JJTI_MN_bots_real_mt5_vps.md", "JJTI", 24),
    ]:
        records = parse_records(ROOT / "docs" / archivo, cuenta)
        magics = [record.magic_number for record in records]
        assert len(magics) == esperados
        duplicados = sorted({magic for magic in magics if magics.count(magic) > 1})
        assert not duplicados, f"{cuenta} conserva magics duplicados tras la migracion: {duplicados}"


def test_post_migration_comment_carries_its_own_magic() -> None:
    """La identidad aprobada es `<label>_MN<magic>`: el comment y el magic no pueden
    discrepar, porque el comment es lo unico que MT5 escribe en cada operacion."""
    for archivo, cuenta in [
        ("registro_BEPB_MN_bots_real_mt5_vps.md", "BEPB"),
        ("registro_JJTI_MN_bots_real_mt5_vps.md", "JJTI"),
    ]:
        for record in parse_records(ROOT / "docs" / archivo, cuenta):
            assert record.comment_identity.endswith(f"_MN{record.magic_number}"), (
                f"{cuenta}: el comment {record.comment_identity!r} no declara su magic "
                f"{record.magic_number}"
            )


def test_pre_migration_collision_survives_in_the_sealed_manifest() -> None:
    """La evidencia historica no se reescribe: el manifiesto sellado antes de la migracion
    conserva las dos filas que compartian `magic=10827` y que quedaron WITHHELD (G13-14)."""
    manifiesto = SEALED_INVENTORY / "bepb_magic_manifest.json"
    if not manifiesto.exists():
        # `runtime/` es evidencia local ignorada por Git: en CI el fichero no existe y esta
        # propiedad no se puede comprobar. No se sustituye por un fixture inventado.
        return
    registros = json.loads(manifiesto.read_text(encoding="utf-8"))["records"]
    colisionan = [r for r in registros if r.get("magic_number") == PRE_MIGRATION_COLLIDING_MAGIC]
    assert len(colisionan) == 2, (
        "el manifiesto sellado debe conservar la colision pre-migracion tal como se observo"
    )


def test_migration_resolved_the_bepb_collision() -> None:
    """Cierre del hecho anterior: en el estado post-migracion ese magic identifica a un solo
    EA, porque `DAX40H1stat_5.29.24` se movio a 10829."""
    records = parse_records(ROOT / "docs" / "registro_BEPB_MN_bots_real_mt5_vps.md", "BEPB")
    con_magic = [r for r in records if r.magic_number == PRE_MIGRATION_COLLIDING_MAGIC]
    assert len(con_magic) == 1
    assert con_magic[0].comment_identity == "DAXH1_5.27.28_MN10827"
    reasignado = [r for r in records if r.comment_identity == "DAXH1_5.29.24_MN10829"]
    assert len(reasignado) == 1
    assert reasignado[0].magic_number == 10829
