"""Reevalúa resultados F7 ya sellados con el contrato direccional vigente.

No ejecuta MT5, no cambia el manifiesto original ni promueve bots externos. Produce
un artefacto append-only que enlaza cada run-manifest verificado con su veredicto
original y el recalculado bajo un hash explícito de configuración.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from record_operational_backtest import load_manifest, seal_payload

METRIC_PATTERN = re.compile(
    r"^(Net Profit|Profit Factor|Max DD %|# Trades)\s+([0-9,.]+)\s+([0-9,.]+)",
    re.MULTILINE,
)
METRIC_KEYS = {
    "Net Profit": "net_profit",
    "Profit Factor": "profit_factor",
    "Max DD %": "max_dd_pct",
    "# Trades": "num_trades",
}


def _number(raw: str) -> float:
    return float(raw.replace(",", ""))


def extract_metrics(stdout: str) -> dict[str, tuple[float, float]]:
    metrics = {
        METRIC_KEYS[label]: (_number(sqx), _number(mt5))
        for label, sqx, mt5 in METRIC_PATTERN.findall(stdout)
    }
    if set(metrics) != set(METRIC_KEYS.values()):
        missing = sorted(set(METRIC_KEYS.values()) - set(metrics))
        raise ValueError(f"métricas no reconstruibles desde la evidencia: {missing}")
    return metrics


def config_sha256(config_path: Path) -> str:
    return hashlib.sha256(config_path.read_bytes()).hexdigest()


def _fuente_desaparecida(raw_manifest: dict[str, Any]) -> str | None:
    """Ruta de la fuente si la corrida pertenece a una campaña ya superseded.

    El renombrado MN movió las carpetas de estrategia bajo
    `user/Estrategias_script_mt5_real_BEPB_y_JJTI/`, así que un `sqx_path` que ya no existe
    identifica una comparación de la campaña **anterior**. Esas corridas conservan su
    evidencia sellada y su veredicto sigue siendo válido para lo que se midió entonces,
    pero no forman parte de la campaña vigente y nunca se registraron en la base.

    Se comprueba la existencia del fichero, no el nombre: un criterio por patrón de nombre
    se rompería con el próximo renombrado.
    """
    source = raw_manifest.get("source") or {}
    for clave in ("sqx_path", "mq5_path"):
        ruta = source.get(clave)
        if isinstance(ruta, str) and ruta and not Path(ruta).exists():
            return ruta
    return None


def reclassify(manifest_root: Path, panel_dir: Path, config_path: Path) -> dict[str, Any]:
    sys.path.insert(0, str(panel_dir))
    import compare_sqx_vs_mt5 as comparator
    import sqx_mt5_config as config

    configured = config.cargar()
    comparator.UMBRALES = configured["umbrales"]
    entries: list[dict[str, Any]] = []
    superseded: list[dict[str, str]] = []
    for manifest_path in sorted(manifest_root.rglob("run-manifest.json")):
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if raw_manifest.get("mode") != "launch" or raw_manifest.get("result", {}).get("returncode") != 0:
            continue
        obsoleta = _fuente_desaparecida(raw_manifest)
        if obsoleta is not None:
            # Campaña superseded: el renombrado MN movió las carpetas de estrategia, así que
            # una corrida cuya fuente ya no existe pertenece a la campaña anterior. Su
            # veredicto se recalcularía igual de bien --el manifiesto está sellado-- pero
            # infla el recuento y obliga a retener una entrada en cada persistencia, porque
            # esas corridas nunca llegaron a registrarse en la base. Se listan aparte.
            superseded.append({"run_id": raw_manifest.get("run_id", manifest_path.parent.name),
                               "missing_source": obsoleta})
            continue
        manifest, original_verdict = load_manifest(manifest_path)
        metrics = extract_metrics(str(manifest["result"]["stdout"]))
        evaluations = {
            key: comparator.evaluar_metrica(key, sqx, mt5)
            for key, (sqx, mt5) in metrics.items()
        }
        recalculated, detail = comparator.veredicto_de(
            {key: value["ok"] for key, value in evaluations.items()}
        )
        entries.append({
            "run_id": manifest["run_id"],
            "source_manifest_sha256": manifest["manifest_sha256"],
            "original_verdict": original_verdict,
            "reclassified_verdict": recalculated,
            "detail": detail,
            "metrics": {
                key: {
                    "sqx": metrics[key][0], "mt5": metrics[key][1],
                    "variation_pct": value["variacion"],
                    "direction": value["direccion"],
                    "limit_pct": value["umbral"], "passed": value["ok"],
                }
                for key, value in evaluations.items()
            },
        })
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "purpose": "SQX_MT5_DIRECTIONAL_RECLASSIFICATION",
        "panel_config_path": str(config_path),
        "panel_config_sha256": config_sha256(config_path),
        "thresholds": configured["umbrales"],
        "entries": entries,
        "superseded_runs": superseded,
        "summary": {
            "runs": len(entries),
            "changed_verdicts": sum(
                entry["original_verdict"] != entry["reclassified_verdict"] for entry in entries
            ),
            "superseded": len(superseded),
        },
    }
    payload["payload_sha256"] = seal_payload(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-root", type=Path, required=True)
    parser.add_argument("--panel-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = reclassify(
        args.manifest_root.resolve(), args.panel_dir.resolve(), args.config.resolve()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"runs={payload['summary']['runs']} changed={payload['summary']['changed_verdicts']} "
        f"seal={payload['payload_sha256']} output={args.output}"
    )


if __name__ == "__main__":
    main()
