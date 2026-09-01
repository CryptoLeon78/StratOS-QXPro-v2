"""Lanzador trazable de SQX_vs_MT5 para artefactos admitidos en StratOS.

Nunca despliega EAs. Un terminal real sólo puede usarse como *Strategy Tester*
si el operador lo autoriza en cada lanzamiento, AutoTrading está desactivado y
ningún terminal MT5 está abierto. Los resultados se guardan fuera de las fuentes
de Análisis y se sellan con SHA-256 para su posterior registro append-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_START_DATE = "2018-01-01"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_safe_terminal(terminal: dict[str, Any] | None, expected_terminal: str, allow_real: bool) -> None:
    if terminal is None:
        raise ValueError("SQX_vs_MT5 no tiene terminal_backtest utilizable")
    if terminal.get("id") != expected_terminal:
        raise ValueError("terminal_backtest distinto del terminal autorizado para esta corrida")
    if terminal.get("algotrading") is not False:
        raise ValueError("AutoTrading debe estar desactivado para usar el Strategy Tester operacional")
    if terminal.get("es_real") and not allow_real:
        raise ValueError("un terminal real exige --allow-real-strategy-tester explícito")


def resolve_symbol_for_ticks(config: Any, cfg: dict[str, Any], symbol: str) -> str | None:
    """Resuelve sólo por alias guardado o por coincidencia exacta de ticks."""
    clean = config.limpiar_sufijo_broker(symbol)
    aliases = cfg.get("alias_simbolos") or {}
    mapped = aliases.get(clean) or aliases.get(symbol)
    candidates = [candidate for candidate in (mapped, clean) if candidate]
    terminal = config.terminal(cfg, "terminal_backtest")
    ticks_dir = config.ticks_de(terminal) if terminal else None
    if not ticks_dir or not ticks_dir.is_dir():
        return None
    names = {path.name.casefold(): path.name for path in ticks_dir.iterdir() if path.is_dir()}
    return next((names[candidate.casefold()] for candidate in candidates if candidate.casefold() in names), None)


def close_target_terminal(compare: Any, terminal_exe: str) -> bool:
    """Solicita cierre limpio de la instancia de Tester y espera su salida.

    No usa ``Stop-Process``: si MT5 no acepta el cierre de ventana, el caller
    falla cerrado y conserva el control humano en vez de matar una sesión.
    """
    command = (
        "$target = $args[0]; "
        "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -eq $target } | "
        "ForEach-Object { $_.CloseMainWindow() | Out-Null }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command, terminal_exe],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    deadline = time.monotonic() + 30
    while compare.terminal_abierto(terminal_exe) and time.monotonic() < deadline:
        time.sleep(0.25)
    return not compare.terminal_abierto(terminal_exe)


def build_command(
    *, panel_dir: Path, sqx_path: Path, mq5_path: Path, output_dir: Path,
    since: str, until: str, symbol: str, timeframe: str, sqx_trades_csv: Path | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(panel_dir / "compare_sqx_vs_mt5.py"),
        "--sqx-path", str(sqx_path),
        "--mq5-path", str(mq5_path),
        "--symbol", symbol,
        "--timeframe", timeframe,
        "--from", since,
        "--to", until,
        "--output-dir", str(output_dir),
        "--non-interactive",
        "--strict-real-ticks",
    ]
    if sqx_trades_csv:
        command.extend(["--sqx-trades-csv", str(sqx_trades_csv)])
    return command


def write_manifest(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload["manifest_sha256"] = seal_payload(payload)
    target = output_dir / "run-manifest.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, required=True)
    parser.add_argument("--sqx", type=Path, required=True)
    parser.add_argument("--mq5", type=Path, required=True)
    parser.add_argument(
        "--sqx-trades-csv", type=Path,
        help="CSV sellado de operaciones exportado por AlgoWizard; permite .sqx sin orders.bin.",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-terminal", required=True)
    parser.add_argument("--from", dest="since", default=DEFAULT_START_DATE)
    parser.add_argument("--to", dest="until", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--allow-real-strategy-tester", action="store_true")
    parser.add_argument(
        "--manage-backtest-terminal",
        action="store_true",
        help="Solicita el cierre limpio de la instancia objetivo antes del Tester.",
    )
    parser.add_argument("--launch", action="store_true", help="Ejecuta MT5; por defecto sólo preflight.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel_dir = args.panel_dir.resolve()
    sqx_path, mq5_path = args.sqx.resolve(), args.mq5.resolve()
    sqx_trades_csv = args.sqx_trades_csv.resolve() if args.sqx_trades_csv else None
    if not (panel_dir / "compare_sqx_vs_mt5.py").is_file():
        raise SystemExit("panel-dir no contiene compare_sqx_vs_mt5.py")
    if not sqx_path.is_file() or not mq5_path.is_file():
        raise SystemExit("las fuentes .sqx y .mq5 deben existir")
    if sqx_trades_csv and not sqx_trades_csv.is_file():
        raise SystemExit("el CSV de operaciones de SQX debe existir")

    sys.path.insert(0, str(panel_dir))
    import compare_sqx_vs_mt5 as compare  # noqa: PLC0415
    import sqx_mt5_config as config  # noqa: PLC0415

    cfg = config.cargar(forzar=True)
    terminal = config.terminal(cfg, "terminal_backtest")
    try:
        assert_safe_terminal(terminal, args.expected_terminal, args.allow_real_strategy_tester)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.launch and compare.terminal_abierto(terminal["exe"]):
        if not args.manage_backtest_terminal:
            raise SystemExit("el terminal MT5 de backtest está abierto; use --manage-backtest-terminal autorizado")
        if not close_target_terminal(compare, terminal["exe"]):
            raise SystemExit("MT5 no aceptó el cierre limpio de la instancia de backtest")

    # El preflight replica las precondiciones de --strict-real-ticks sin compilar
    # ni abrir MT5. Así una cola no deja resultados ambiguos por M1-OHLC.
    compare.aplicar_config(cfg)
    sqx = compare.cargar_lado_sqx(sqx_path, sqx_trades_csv)
    sqx_symbol, timeframe = sqx["simbolo"], sqx["timeframe"]
    if not sqx_symbol or not timeframe:
        raise SystemExit("no se pudo extraer símbolo/timeframe del .sqx; queda WITHHELD")
    symbol = resolve_symbol_for_ticks(config, cfg, sqx_symbol)
    if not symbol:
        raise SystemExit("no hay alias o ticks reales para el símbolo; queda WITHHELD")
    ticks = compare.cobertura_ticks(symbol)
    since_dt, until_dt = compare.parsear_fecha(args.since), compare.parsear_fecha(args.until)
    if since_dt is None or until_dt is None or since_dt >= until_dt:
        raise SystemExit("rango de backtest inválido")
    if not ticks or since_dt < ticks[0] or until_dt > ticks[1]:
        raise SystemExit("el rango 2018-actual exige ticks reales completos; queda WITHHELD")

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + sha256_file(sqx_path)[:12]
    output_dir = args.output_root.resolve() / run_id
    command = build_command(
        panel_dir=panel_dir,
        sqx_path=sqx_path,
        mq5_path=mq5_path,
        output_dir=output_dir,
        since=args.since,
        until=args.until,
        symbol=symbol,
        timeframe=timeframe,
        sqx_trades_csv=sqx_trades_csv,
    )
    payload: dict[str, Any] = {
        "run_id": run_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "mode": "launch" if args.launch else "preflight",
        "terminal": {
            "id": terminal["id"],
            "name": terminal["nombre"],
            "algotrading": terminal["algotrading"],
            "is_real": terminal["es_real"],
        },
        "source": {
            "sqx_path": str(sqx_path),
            "mq5_path": str(mq5_path),
            "sqx_sha256": sha256_file(sqx_path),
            "mq5_sha256": sha256_file(mq5_path),
            **({"sqx_trades_csv": str(sqx_trades_csv), "sqx_trades_csv_sha256": sha256_file(sqx_trades_csv)}
               if sqx_trades_csv else {}),
        },
        "range": {"from": args.since, "to": args.until, "real_ticks_required": True},
        "strategy": {
            "symbol": symbol,
            "timeframe": timeframe,
            "ticks_from": ticks[0].isoformat(),
            "ticks_to": ticks[1].isoformat(),
        },
        "command": command,
    }
    if not args.launch:
        manifest = write_manifest(output_dir, payload)
        print(f"preflight=ok manifest={manifest}")
        return

    result = subprocess.run(command, cwd=panel_dir, text=True, capture_output=True, timeout=4 * 3600)
    payload["result"] = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    payload["artifacts"] = [
        {"path": str(path), "sha256": sha256_file(path)}
        for path in sorted(output_dir.glob("*"))
        if path.is_file()
    ]
    manifest = write_manifest(output_dir, payload)
    if result.returncode:
        raise SystemExit(f"SQX_vs_MT5 falló; evidencia sellada: {manifest}")
    print(f"backtest=ok manifest={manifest}")


if __name__ == "__main__":
    main()
