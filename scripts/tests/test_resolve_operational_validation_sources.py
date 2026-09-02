import hashlib
from pathlib import Path
from zipfile import ZipFile

from resolve_operational_validation_sources import resolve_sources

LAYOUT = {
    "version": "test",
    "project_name_prefix": "Project_",
    "project_definition_filename": "project.cfx",
    "databanks_directory_name": "databanks",
    "strategy_extension": ".sqx",
    "mining_task_type": "Build",
}


def _definicion_con_tareas(project: Path, *tipos: str) -> None:
    """Escribe un `project.cfx` real (zip con `config.xml`) declarando esas tareas."""
    tareas = "".join(f'<Task type="{tipo}" name="t{i}" active="true" />' for i, tipo in enumerate(tipos))
    with ZipFile(project / "project.cfx", "w") as archive:
        archive.writestr("config.xml", f"<Project><Tasks>{tareas}</Tasks></Project>")


def _inventory(candidate: Path) -> dict[str, object]:
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    return {
        "items": [
            {
                "status": "STATIC_VALIDATED",
                "strategy_name": candidate.stem,
                "sqx_path": str(candidate),
                "sqx_sha256": digest,
                "mql5_path": str(candidate.with_suffix(".mq5")),
                "mql5_sha256": "mql5",
                "symbol": "AUDCAD",
                "timeframe": "H4",
            }
        ]
    }


def _project(root: Path, name: str, candidate: Path) -> Path:
    project = root / name
    databanks = project / "databanks"
    databanks.mkdir(parents=True)
    (project / "project.cfx").write_bytes(b"definition")
    forward = databanks / "Forward"
    forward.mkdir()
    (forward / candidate.name).write_bytes(candidate.read_bytes())
    wfm = databanks / "WFM"
    wfm.mkdir()
    (wfm / "Strategy 1.2.3.sqx").write_bytes(b"wfm")
    return project


def test_resolver_requires_unique_project_hash_match(tmp_path: Path) -> None:
    candidate = tmp_path / "AUDCADH4S_Strategy 1.2.3.sqx"
    candidate.write_bytes(b"candidate")
    projects = tmp_path / "projects"
    _project(projects, "Project_A", candidate)

    rows = resolve_sources(_inventory(candidate), projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "RESOLVED"
    assert rows[0]["project_path"].endswith("Project_A")
    assert {item["databank_bucket"] for item in rows[0]["validation_artifacts"]} == {
        "Forward",
        "WFM",
    }


def test_resolver_withholds_ambiguous_hash_match(tmp_path: Path) -> None:
    candidate = tmp_path / "AUDCADH4S_Strategy 1.2.3.sqx"
    candidate.write_bytes(b"candidate")
    projects = tmp_path / "projects"
    _project(projects, "Project_A", candidate)
    _project(projects, "Project_B", candidate)

    rows = resolve_sources(_inventory(candidate), projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "WITHHELD"
    assert rows[0]["reason"] == "AMBIGUOUS_PROJECT_HASH_MATCH"


def test_resolver_withholds_candidate_without_project_hash_match(tmp_path: Path) -> None:
    candidate = tmp_path / "AUDCADH4S_Strategy 1.2.3.sqx"
    candidate.write_bytes(b"candidate")
    projects = tmp_path / "projects"
    unrelated = tmp_path / "unrelated.sqx"
    unrelated.write_bytes(b"other")
    _project(projects, "Project_A", unrelated)

    rows = resolve_sources(_inventory(candidate), projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "WITHHELD"
    assert rows[0]["reason"] == "NO_PROJECT_HASH_MATCH"


def test_resolver_accepts_history_signature_when_export_metadata_differs(tmp_path: Path) -> None:
    candidate = tmp_path / "AUDCADH4S_Strategy 1.2.3.sqx"
    with ZipFile(candidate, "w") as archive:
        archive.writestr("orders.bin", b"orders")
        archive.writestr("lastSettings.xml", b"settings")
        archive.writestr("strategy_Portfolio.xml", b"candidate-metadata")
    projects = tmp_path / "projects"
    project = projects / "Project_A"
    source = project / "databanks" / "Forward"
    source.mkdir(parents=True)
    (project / "project.cfx").write_bytes(b"definition")
    with ZipFile(source / candidate.name, "w") as archive:
        archive.writestr("orders.bin", b"orders")
        archive.writestr("lastSettings.xml", b"settings")
        archive.writestr("strategy_Portfolio.xml", b"reexported-metadata")

    rows = resolve_sources(_inventory(candidate), projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "RESOLVED"
    assert rows[0]["source_matches"][0]["match_type"] == "SQX_HISTORY_SIGNATURE"


def test_resolver_uses_source_lineage_only_after_history_signature(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis" / "AUDCAD_H4_S" / "Forward_finalistas"
    analysis.mkdir(parents=True)
    candidate = analysis / "AUDCADH4S_Strategy 1.2.3.sqx"
    candidate.write_bytes(b"candidate")
    projects = tmp_path / "projects"
    _project(projects, "Project_AUDCAD_H4_S", candidate)
    _project(projects, "PortfolioSeleccion", candidate)
    inventory = _inventory(candidate)
    inventory["items"][0]["source_root"] = str(tmp_path / "analysis")

    rows = resolve_sources(inventory, projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "RESOLVED"
    assert rows[0]["project_path"].endswith("Project_AUDCAD_H4_S")
    assert rows[0]["source_selection"] == "HISTORY_SIGNATURE_PLUS_SOURCE_LINEAGE"


def test_resolver_descarta_proyecto_sin_tarea_de_minado(tmp_path: Path) -> None:
    """Un proyecto de ensamblaje de portfolio no puede ser el origen de una minada.

    Importa el `.sqx` ya construido, así que su hash coincide igual que en el
    proyecto que lo minó. Sin tarea Build no hay minado posible: descartarlo no
    es una preferencia, es una imposibilidad estructural.
    """
    candidate = tmp_path / "AUDCADH4S_Strategy 1.2.3.sqx"
    candidate.write_bytes(b"candidate")
    projects = tmp_path / "projects"
    origen = _project(projects, "Project_A", candidate)
    consumidor = _project(projects, "PortfolioSeleccion", candidate)
    _definicion_con_tareas(origen, "Build", "Retest")
    _definicion_con_tareas(consumidor, "AutomaticPortfolioBuilder", "CustomAnalysis")

    rows = resolve_sources(_inventory(candidate), projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "RESOLVED"
    assert rows[0]["project_path"].endswith("Project_A")
    assert rows[0]["source_selection"] == "HISTORY_SIGNATURE_PLUS_BUILD_ORIGIN"


def test_resolver_mantiene_la_ambiguedad_si_no_puede_leer_las_definiciones(tmp_path: Path) -> None:
    """No poder leer un `.cfx` no es prueba de que ese proyecto no haya minado.

    El descarte exige leer las tareas y no encontrar la de minado. Con ambas
    definiciones ilegibles la ambigüedad queda intacta en vez de resolverse a
    ciegas por orden de directorio.
    """
    candidate = tmp_path / "AUDCADH4S_Strategy 1.2.3.sqx"
    candidate.write_bytes(b"candidate")
    projects = tmp_path / "projects"
    _project(projects, "Project_A", candidate)
    _project(projects, "PortfolioSeleccion", candidate)

    rows = resolve_sources(_inventory(candidate), projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "WITHHELD"
    assert rows[0]["reason"] == "AMBIGUOUS_PROJECT_HASH_MATCH"


def test_resolver_no_descarta_el_unico_proyecto_aunque_no_declare_minado(tmp_path: Path) -> None:
    """Sin empate no hay nada que desempatar: el descarte sólo actúa sobre varios."""
    candidate = tmp_path / "AUDCADH4S_Strategy 1.2.3.sqx"
    candidate.write_bytes(b"candidate")
    projects = tmp_path / "projects"
    unico = _project(projects, "PortfolioSeleccion", candidate)
    _definicion_con_tareas(unico, "AutomaticPortfolioBuilder")

    rows = resolve_sources(_inventory(candidate), projects_root=projects, layout=LAYOUT)

    assert rows[0]["status"] == "RESOLVED"
