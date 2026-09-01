"""Extrae evidencia cuantitativa reproducible de databanks SQX144 resueltos.

La herramienta no acepta nombres de carpetas como prueba de WFM, Monte Carlo
o costes. Lee los artefactos SQX que el resolutor ya asoció, verifica sus
hashes y sella el resultado. La razón OOS/IS de la celda activa WFM se conserva
como métrica derivada informativa, sin equipararla al gate F2 hasta que exista
una equivalencia validada. Monte Carlo se recalcula sobre los PnL de ``RETEST
OOS`` con la semilla/número de simulaciones contractuales; costes se toman de
la configuración de prueba SQX efectivamente almacenada en ``lastSettings.xml``.

No escribe en SQX, MT5 ni en la base de datos operacional.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
import sys
import xml.etree.ElementTree as etree
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SOURCE = REPO_ROOT / "core-engine" / "src"
if str(CORE_SOURCE) not in sys.path:
    sys.path.insert(0, str(CORE_SOURCE))

from core.formulas.portfolio import monte_carlo_maxdd  # noqa: E402
from core.services.sqx_baseline_parser import (  # noqa: E402
    _parse_trades,
    parse_sqx144_baseline,
)

VERSION = "operational-validation-evidence-v2"
SQSTATS_NET_PROFIT_INDEX = 10
SQSTATS_SUPPORTED_VERSIONS = {1, 2}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON objeto requerido: {path}")
    return data


def validate_artifact(raw: dict[str, Any]) -> dict[str, str]:
    path = Path(str(raw.get("path", "")))
    expected = raw.get("sha256")
    if not path.is_file() or not isinstance(expected, str):
        raise ValueError("artefacto ausente o sin hash declarado")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError("hash del artefacto no coincide con el manifiesto")
    return {"path": str(path.resolve()), "sha256": actual}


def preferred_artifact(item: dict[str, Any], bucket: str) -> dict[str, Any]:
    # Forward es la fuente que el resolutor demostró contra la exportación de
    # Análisis. Si el databank conserva variantes adicionales, esa coincidencia
    # directa prevalece; nunca se resuelve el empate por orden de directorio.
    if bucket == "Forward":
        source_matches = [
            artifact
            for artifact in item.get("source_matches", [])
            if isinstance(artifact, dict) and artifact.get("databank_bucket") == bucket
        ]
        if len(source_matches) == 1:
            return source_matches[0]
        if len(source_matches) > 1:
            raise ValueError(f"{bucket}: source_matches ambiguos ({len(source_matches)} variantes)")
    candidates = [
        artifact
        for artifact in item.get("validation_artifacts", [])
        if isinstance(artifact, dict) and artifact.get("databank_bucket") == bucket
    ]
    if not candidates:
        raise ValueError(f"{bucket}: artefacto no resuelto")
    identifier = str(item.get("strategy_identifier", ""))
    strategy_name = str(item.get("strategy_name", ""))
    # El identificador normalizado de inventario puede omitir un sufijo entre
    # paréntesis. La identidad completa después de ``Strategy `` conserva esa
    # variante y permite escoger exactamente su WFM, sin basarse en orden.
    strategy_suffix = strategy_name.partition("Strategy ")[2]
    if strategy_suffix:
        full_name = f"Strategy {strategy_suffix}.sqx"
        full_matches = [
            artifact
            for artifact in candidates
            if Path(str(artifact.get("path", ""))).name == full_name
        ]
        if len(full_matches) == 1:
            return full_matches[0]
        if len(full_matches) > 1:
            raise ValueError(f"{bucket}: identidad completa ambigua ({len(full_matches)} variantes)")
    exact_names = {f"Strategy {identifier}.sqx", f"Strategy {identifier}"}
    exact = [artifact for artifact in candidates if Path(str(artifact.get("path", ""))).name in exact_names]
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(f"{bucket}: selección ambigua ({len(candidates)} variantes)")


def _skip_modified_utf(raw: bytes, offset: int) -> int:
    if offset + 2 > len(raw):
        raise ValueError("SQStats UTF truncado")
    size = struct.unpack_from(">H", raw, offset)[0]
    end = offset + 2 + size
    if end > len(raw):
        raise ValueError("SQStats UTF truncado")
    return end


def sqstats_net_profit(element: etree.Element) -> float:
    """Lee NetProfit de SQStats compacto v1/v2 sin heurística de texto.

    SQX144 serializa cada valor como tipo, índice y payload. El índice 10 es
    ``NetProfit`` en ``StatsKeyCache`` de la instalación SQX144 local. Sólo
    se acepta esa versión/formato, para que un cambio de SQX quede retenido.
    """
    if element.tag != "SQStats" or element.get("e") != "b64":
        raise ValueError("SQStats compacto requerido")
    try:
        version = int(element.get("version", "1"))
    except ValueError as exc:
        raise ValueError("versión SQStats inválida") from exc
    if version not in SQSTATS_SUPPORTED_VERSIONS:
        raise ValueError(f"versión SQStats no soportada: {version}")
    try:
        raw = base64.b64decode((element.text or "").strip(), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("payload SQStats base64 inválido") from exc
    offset = 0
    net_profit: float | None = None
    while offset < len(raw):
        record_type = raw[offset]
        offset += 1
        if record_type == 1:
            offset += 1 + 4
        elif record_type == 2:
            offset += 1 + 8
        elif record_type == 3:
            if offset + 5 > len(raw):
                raise ValueError("registro SQStats double truncado")
            index = raw[offset]
            value = struct.unpack_from(">f" if version > 1 else ">d", raw, offset + 1)[0]
            offset += 1 + (4 if version > 1 else 8)
            if index == SQSTATS_NET_PROFIT_INDEX:
                net_profit = float(value)
        elif record_type == 101:
            offset = _skip_modified_utf(raw, offset) + 4
        elif record_type == 102:
            offset = _skip_modified_utf(raw, offset) + 8
        elif record_type == 103:
            offset = _skip_modified_utf(raw, offset) + (4 if version > 1 else 8)
        else:
            raise ValueError(f"tipo SQStats desconocido: {record_type}")
        if offset > len(raw):
            raise ValueError("registro SQStats truncado")
    if net_profit is None or not math.isfinite(net_profit):
        raise ValueError("NetProfit no disponible en SQStats")
    return net_profit


def wfe_evidence(artifact: dict[str, str]) -> dict[str, Any]:
    with zipfile.ZipFile(artifact["path"]) as archive:
        try:
            root = etree.fromstring(archive.read("settings.xml"))
        except KeyError as exc:
            raise ValueError("WFM sin settings.xml") from exc
    matrix = root.find(".//WalkForwardResult/MatrixResult")
    if matrix is None:
        raise ValueError("WalkForwardMatrixResult ausente")
    try:
        start_1, increment_1, active_1 = (
            int(matrix.attrib["start1"]),
            int(matrix.attrib["increment1"]),
            int(matrix.attrib["activeParam1"]),
        )
        start_2, increment_2, active_2 = (
            int(matrix.attrib["start2"]),
            int(matrix.attrib["increment2"]),
            int(matrix.attrib["activeParam2"]),
        )
    except (KeyError, ValueError) as exc:
        raise ValueError("parámetros activos WFM inválidos") from exc
    selected = (start_1 + increment_1 * active_1, start_2 + increment_2 * active_2)
    values: list[float] = []
    selected_value: float | None = None
    for run in matrix.findall("RunResult"):
        try:
            is_profit = sqstats_net_profit(run.find("stats/SQStats"))  # type: ignore[arg-type]
            oos_profit = sqstats_net_profit(run.find("statsOOS/SQStats"))  # type: ignore[arg-type]
            if is_profit == 0:
                continue
            value = oos_profit / is_profit
            if not math.isfinite(value):
                continue
            values.append(value)
            if (int(run.attrib["param1"]), int(run.attrib["param2"])) == selected:
                selected_value = value
        except (KeyError, TypeError, ValueError):
            continue
    if selected_value is None:
        raise ValueError("celda WFM activa sin WFE decodificable")
    return {
        "status": "DERIVED_UNMAPPED",
        "informational": True,
        "non_blocking": True,
        "f2_gate_status": "NOT_APPLICABLE",
        "f2_gate_note": (
            "La razón OOS/IS de la celda WFM no es equivalente al WFE F2 de StratOS "
            "sin una equivalencia explícita validada o evidencia forward/MT5."
        ),
        "value": selected_value,
        "artifact_path": artifact["path"],
        "sha256": artifact["sha256"],
        "method": "SQX144_WFM_ACTIVE_CELL_NET_PROFIT_OOS_DIV_IS",
        "selected_parameters": {"oos_pct": selected[0], "runs": selected[1]},
        "matrix_summary": {
            "decodable_cells": len(values),
            "min": min(values),
            "median": median(values),
            "max": max(values),
        },
    }


def _enabled(value: str | None) -> bool:
    return str(value).strip().lower() == "true"


def _wfm_acceptance_conditions(element: etree.Element) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for condition in element.findall("Condition"):
        left = condition.find("./Left-Side/Column-Value")
        comparator_element = condition.find("./Comparator")
        comparator = (
            None
            if comparator_element is None
            else comparator_element.get("value") or comparator_element.text
        )
        numeric = condition.find("./Right-Side/Numeric-Value")
        right_column = condition.find("./Right-Side/Column-Value")
        if left is None or comparator is None or (numeric is None and right_column is None):
            raise ValueError("condición WFM incompleta")
        conditions.append(
            {
                "enabled": _enabled(condition.get("use")),
                "left": dict(left.attrib),
                "comparator": comparator,
                "right": (
                    {"numeric": numeric.get("value")}
                    if numeric is not None
                    else {"column": dict(right_column.attrib)}
                ),
            }
        )
    if not conditions:
        raise ValueError("condiciones WFM ausentes")
    return conditions


def wfm_project_criteria(project_definition: dict[str, Any]) -> dict[str, Any]:
    """Extrae del ``project.cfx`` los criterios SQX reales del WFM activo.

    No usa el nombre de proyecto ni valores de este caso: busca exactamente una
    tarea Retest cuyo XML tenga ``WalkForwardMatrix use=true`` y conserva sus
    atributos junto con las condiciones de aceptación ``CrossCheck``.
    """
    project = validate_artifact(project_definition)
    with zipfile.ZipFile(project["path"]) as archive:
        try:
            config_root = etree.fromstring(archive.read("config.xml"))
        except KeyError as exc:
            raise ValueError("project.cfx sin config.xml") from exc
        candidates: list[dict[str, Any]] = []
        for task in config_root.findall(".//Task"):
            if task.get("type") != "Retest":
                continue
            task_xml = task.get("taskXMLFile")
            if not task_xml:
                continue
            try:
                task_root = etree.fromstring(archive.read(task_xml))
            except KeyError as exc:
                raise ValueError(f"project.cfx sin tarea WFM declarada: {task_xml}") from exc
            matrix = task_root.find(".//WalkForwardMatrix")
            if matrix is None or not _enabled(matrix.get("use")):
                continue
            acceptance = [
                element
                for element in task_root.findall(".//Conditions")
                if element.get("CrossCheck") == "WalkForwardMatrix"
            ]
            if len(acceptance) != 1:
                raise ValueError("criterio de aceptación WFM no único")
            walk_forward = matrix.find("./Settings/WalkForward")
            if walk_forward is None:
                raise ValueError("configuración WalkForward WFM ausente")
            candidates.append(
                {
                    "task": {
                        "name": task.get("name"),
                        "title": task.get("title"),
                        "xml": task_xml,
                    },
                    "walk_forward_matrix": dict(matrix.attrib),
                    "walk_forward": dict(walk_forward.attrib),
                    "parameter_grid": [dict(param.attrib) for param in walk_forward],
                    "acceptance": dict(acceptance[0].attrib),
                    "acceptance_conditions": _wfm_acceptance_conditions(acceptance[0]),
                }
            )
    if len(candidates) != 1:
        raise ValueError(f"tarea WFM activa no única ({len(candidates)})")
    return {
        "project_definition": project,
        "criteria": candidates[0],
    }


def static_validated_wfm(
    item: dict[str, Any], wfm_artifact: dict[str, str]
) -> dict[str, Any]:
    project_definition = item.get("project_definition")
    if not isinstance(project_definition, dict):
        raise ValueError("project_definition WFM ausente")
    criteria = wfm_project_criteria(project_definition)
    # Decodificar la matriz confirma que el artefacto elegido conserva una celda
    # activa; el resultado se marca derivado, no como sustituto del contrato F2.
    wfe_evidence(wfm_artifact)
    return {
        "status": "STATIC_VALIDATED_WFM",
        "method": "SQX_RETEST_WALK_FORWARD_MATRIX_PROJECT_CRITERIA",
        "validation_basis": "SEALED_WFM_DATABANK_ARTIFACT_AND_PROJECT_ACCEPTANCE_CRITERIA",
        "artifact_path": wfm_artifact["path"],
        "sha256": wfm_artifact["sha256"],
        **criteria,
    }


def monte_carlo_evidence(artifact: dict[str, str], *, n_sims: int, seed: int) -> dict[str, Any]:
    payload = Path(artifact["path"]).read_bytes()
    baseline = parse_sqx144_baseline(payload)
    with zipfile.ZipFile(Path(artifact["path"])) as archive:
        trades = _parse_trades(archive.read("orders.bin"))
    result = monte_carlo_maxdd(
        [Decimal(str(row[2])) for row in trades],
        n_sims=n_sims,
        seed=seed,
        initial_equity=Decimal(str(_initial_capital(payload))),
    )
    p95 = float(result.p95)
    return {
        "p95_no_ruin": p95 < 100.0,
        "p95_max_dd_pct": p95,
        "p75_max_dd_pct": float(result.p75),
        "p50_max_dd_pct": float(result.p50),
        "n_simulations": result.n_simulations,
        "seed": result.seed,
        "trade_count": baseline.trade_count,
        "initial_capital": _initial_capital(payload),
        "artifact_path": artifact["path"],
        "sha256": artifact["sha256"],
        "method": "BOOTSTRAP_TRADE_PNL_WITH_REPLACEMENT",
    }


def _initial_capital(payload: bytes) -> float:
    with zipfile.ZipFile(__import__("io").BytesIO(payload)) as archive:
        root = etree.fromstring(archive.read("lastSettings.xml"))
    text = root.findtext(".//InitialCapital")
    try:
        value = float(str(text))
    except (TypeError, ValueError) as exc:
        raise ValueError("InitialCapital SQX no disponible") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError("InitialCapital SQX inválido")
    return value


def cost_evidence(artifact: dict[str, str]) -> dict[str, Any]:
    payload = Path(artifact["path"]).read_bytes()
    parsed = parse_sqx144_baseline(payload)
    with zipfile.ZipFile(__import__("io").BytesIO(payload)) as archive:
        root = etree.fromstring(archive.read("lastSettings.xml"))
    candidates: list[dict[str, Any]] = []
    for setup in root.findall(".//Setup"):
        chart = setup.find("Chart")
        if chart is None or chart.get("symbol") != parsed.symbol or chart.get("timeframe") != parsed.timeframe:
            continue
        commission = setup.findtext(".//Commissions//Param[@key='Commission']")
        swap = setup.find(".//Swap")
        try:
            values = {
                "session": setup.get("session"),
                "spread": float(str(chart.get("spread"))),
                "slippage": float(str(setup.get("slippage"))),
                "commission": float(str(commission)),
                "swap_enabled": None if swap is None else swap.get("use") == "true",
                "swap_long": None if swap is None else float(str(swap.get("long"))),
                "swap_short": None if swap is None else float(str(swap.get("short"))),
            }
        except (TypeError, ValueError):
            continue
        if values["session"] is not None:
            candidates.append(values)
    if len(candidates) != 1:
        raise ValueError(f"configuración de costes no única para {parsed.symbol}/{parsed.timeframe}")
    values = candidates[0]
    return {
        "session_aware": True,
        "session_scope": values.pop("session"),
        "values": values,
        "artifact_path": artifact["path"],
        "sha256": artifact["sha256"],
        "method": "SQX_LAST_SETTINGS_EFFECTIVE_SETUP",
    }


def baseline_snapshot(artifact: dict[str, str]) -> dict[str, Any]:
    parsed = parse_sqx144_baseline(Path(artifact["path"]).read_bytes())
    return {
        "artifact_path": artifact["path"],
        "sha256": artifact["sha256"],
        "symbol": parsed.symbol,
        "timeframe": parsed.timeframe,
        "backtest_from": parsed.backtest_from,
        "backtest_to": parsed.backtest_to,
        "profit_factor": parsed.profit_factor,
        "expectancy_r": parsed.expectancy_r,
        "sharpe": parsed.sharpe,
        "max_dd_pct": parsed.max_dd_pct,
        "trade_count": parsed.trade_count,
    }


def extract_item(item: dict[str, Any], *, n_sims: int, seed: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "strategy_name": item.get("strategy_name"),
        "sqx_sha256": item.get("sqx_sha256"),
        "source_selection": item.get("source_selection"),
        "evidence_status": "WITHHELD",
        "withheld_reasons": [],
    }
    if item.get("status") != "RESOLVED" or not isinstance(item.get("sqx_sha256"), str):
        result["withheld_reasons"] = ["SOURCE_NOT_RESOLVED"]
        return result
    try:
        forward = validate_artifact(preferred_artifact(item, "Forward"))
        retest_oos = validate_artifact(preferred_artifact(item, "RETEST OOS"))
        wfm = validate_artifact(preferred_artifact(item, "WFM"))
        result["baselines"] = {
            "forward": baseline_snapshot(forward),
            "retest_oos": baseline_snapshot(retest_oos),
        }
        result["sqx_validation"] = static_validated_wfm(item, wfm)
        result["wfe"] = wfe_evidence(wfm)
        result["monte_carlo"] = monte_carlo_evidence(retest_oos, n_sims=n_sims, seed=seed)
        result["costs"] = cost_evidence(forward)
        result["evidence_status"] = "EXTRACTED"
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        result["withheld_reasons"] = [f"EXTRACTION_FAILED:{exc}"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-manifest", type=Path, required=True)
    parser.add_argument("--thresholds", type=Path, default=Path("config/thresholds.seed.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_manifest = load_object(args.sources_manifest)
    items = source_manifest.get("items")
    if not isinstance(items, list):
        raise SystemExit("sources-manifest requiere items")
    thresholds = load_object(args.thresholds)
    n_sims, seed = thresholds.get("mc_sims"), thresholds.get("mc_seed")
    if not isinstance(n_sims, int) or n_sims < 1 or not isinstance(seed, int):
        raise SystemExit("thresholds requiere mc_sims entero positivo y mc_seed entero")

    extracted = [extract_item(item, n_sims=n_sims, seed=seed) for item in items if isinstance(item, dict)]
    payload = {
        "version": VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "sources_manifest": {
            "path": str(args.sources_manifest.resolve()),
            "sha256": sha256_file(args.sources_manifest),
        },
        "thresholds": {"path": str(args.thresholds.resolve()), "sha256": sha256_file(args.thresholds)},
        "summary": {
            "candidates": len(extracted),
            "extracted": sum(item["evidence_status"] == "EXTRACTED" for item in extracted),
            "withheld": sum(item["evidence_status"] != "EXTRACTED" for item in extracted),
            "static_validated_wfm": sum(
                item.get("sqx_validation", {}).get("status") == "STATIC_VALIDATED_WFM"
                for item in extracted
            ),
        },
        "items": extracted,
    }
    payload["manifest_sha256"] = seal_payload(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"validation evidence extracted={payload['summary']['extracted']} "
        f"withheld={payload['summary']['withheld']} output={args.output}"
    )


if __name__ == "__main__":
    main()
