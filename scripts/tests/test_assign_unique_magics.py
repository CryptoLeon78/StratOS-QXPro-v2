"""Asignación de magics únicos a EAs exportados en lote (backlog A29).

SQX no aleatoriza el `MagicNumber` al exportar varios EAs de golpe: los 28 de `DAX40_m30`
salieron todos con `11111`, el valor por defecto. El inventario los retiene con
`DUPLICATE_MAGIC_NUMBER` porque un magic repetido hace imposible atribuir un trade a su bot
— es el mismo problema que ya se vio con seis EAs del stock compartiendo `11111`.

Reglas: sólo se tocan los duplicados, la asignación es determinista y reproducible, y nunca
se reutiliza un magic ya presente en el conjunto.
"""

from __future__ import annotations

from pathlib import Path

from assign_unique_magics import assign_unique_magics, read_magic

EA = """//+------------------------------------------------------------------+
input int MagicNumber = {magic};  //Magic number
input double Lots = 0.1;
"""


def _ea(carpeta: Path, nombre: str, magic: int) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.mq5"
    ruta.write_text(EA.format(magic=magic), encoding="utf-8")
    return ruta


def test_reads_the_magic_of_an_exported_ea(tmp_path: Path) -> None:
    assert read_magic(_ea(tmp_path, "a", 11111)) == 11111


def test_a_set_without_duplicates_is_left_untouched(tmp_path: Path) -> None:
    _ea(tmp_path, "a", 10)
    _ea(tmp_path, "b", 20)

    cambios = assign_unique_magics(tmp_path, apply=True)

    assert cambios == []
    assert read_magic(tmp_path / "a.mq5") == 10


def test_duplicates_are_reassigned_and_the_first_one_keeps_its_magic(tmp_path: Path) -> None:
    """El primero por nombre conserva el valor: se cambia lo mínimo necesario."""
    _ea(tmp_path, "a", 11111)
    _ea(tmp_path, "b", 11111)
    _ea(tmp_path, "c", 11111)

    cambios = assign_unique_magics(tmp_path, apply=True)

    assert len(cambios) == 2
    magics = [read_magic(tmp_path / f"{n}.mq5") for n in ("a", "b", "c")]
    assert magics[0] == 11111
    assert len(set(magics)) == 3


def test_a_reassigned_magic_never_collides_with_an_existing_one(tmp_path: Path) -> None:
    """Un magic libre en apariencia puede estar en uso por otro EA del conjunto."""
    _ea(tmp_path, "a", 11111)
    _ea(tmp_path, "b", 11111)
    _ea(tmp_path, "ocupado", 11112)

    assign_unique_magics(tmp_path, apply=True)

    magics = [read_magic(p) for p in sorted(tmp_path.glob("*.mq5"))]
    assert len(set(magics)) == len(magics)


def test_it_is_deterministic(tmp_path: Path) -> None:
    """Dos ejecuciones sobre el mismo conjunto proponen exactamente lo mismo."""
    for nombre in ("a", "b", "c"):
        _ea(tmp_path, nombre, 11111)

    primera = assign_unique_magics(tmp_path, apply=False)
    segunda = assign_unique_magics(tmp_path, apply=False)

    assert primera == segunda


def test_a_dry_run_does_not_touch_the_files(tmp_path: Path) -> None:
    _ea(tmp_path, "a", 11111)
    _ea(tmp_path, "b", 11111)

    assign_unique_magics(tmp_path, apply=False)

    assert read_magic(tmp_path / "b.mq5") == 11111


def test_running_twice_is_idempotent(tmp_path: Path) -> None:
    _ea(tmp_path, "a", 11111)
    _ea(tmp_path, "b", 11111)

    assign_unique_magics(tmp_path, apply=True)

    assert assign_unique_magics(tmp_path, apply=True) == []


def test_an_ea_without_a_magic_is_reported_not_guessed(tmp_path: Path) -> None:
    """Sin `MagicNumber` no se inventa uno: el fichero no es un EA exportado normal."""
    (tmp_path / "raro.mq5").write_text("input double Lots = 0.1;", encoding="utf-8")

    assert read_magic(tmp_path / "raro.mq5") is None
    assert assign_unique_magics(tmp_path, apply=True) == []
