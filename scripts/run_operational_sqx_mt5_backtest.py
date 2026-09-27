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
import os
import subprocess
import sys
import time
import csv
import io
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_test_range(sqx_cost: dict[str, Any], since: str | None, until: str | None) -> tuple[str, str]:
    """Prefer the exact SQX setup dates; never silently extend to today's date."""
    start = since or str(sqx_cost.get("date_from") or "").replace(".", "-")
    end = until or str(sqx_cost.get("date_to") or "").replace(".", "-")
    if not start or not end:
        raise ValueError("el rango no está definido en SQX; indique --from y --to explícitamente")
    return start, end


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


CLOSE_ATTEMPT_TIMEOUT_S = 60
CLOSE_SETTLE_CHECK_S = 3
CLOSE_MAX_ATTEMPTS = 5


def close_target_terminal(compare: Any, terminal_exe: str) -> bool:
    """Solicita cierre limpio de la instancia de Tester y espera su salida.

    No usa ``Stop-Process``: si MT5 no acepta el cierre de ventana, el caller
    falla cerrado y conserva el control humano en vez de matar una sesión.

    Reintenta hasta ``CLOSE_MAX_ATTEMPTS`` veces con una confirmación de
    ``CLOSE_SETTLE_CHECK_S`` tras cada cierre aparente. G13-67 (ver
    ASSUMPTIONS.md) documentó relanzamientos del terminal objetivo (PID nuevo)
    justo en esta ventana sin que este script ni ``compare_sqx_vs_mt5.py``
    tocaran la API de MetaTrader5 antes de aquí; la causa confirmada más
    probable es una consulta ``MetaTrader5.initialize()`` ajena (propia
    verificación ad hoc, ``mt5_bridge``, etc.) coincidiendo con el cierre —
    esa llamada lanza el terminal si no encuentra ninguno abierto, efecto
    secundario no documentado de la librería. Se descartó empíricamente un
    servicio Windows o tarea programada como origen (ninguno registrado;
    90s de quietud sin relanzamiento en un entorno limpio). En vez de asumir
    conocido el disparador exacto, el cierre se vuelve auto-reparable ante
    cualquier reaparición transitoria.
    """
    command = (
        "$target = $args[0]; "
        "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -eq $target } | "
        "ForEach-Object { $_.CloseMainWindow() | Out-Null }"
    )
    for _attempt in range(CLOSE_MAX_ATTEMPTS):
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command, terminal_exe],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        deadline = time.monotonic() + CLOSE_ATTEMPT_TIMEOUT_S
        still_open = compare.terminal_abierto(terminal_exe)
        while still_open and time.monotonic() < deadline:
            time.sleep(0.25)
            still_open = compare.terminal_abierto(terminal_exe)
        if still_open:
            continue
        time.sleep(CLOSE_SETTLE_CHECK_S)
        if not compare.terminal_abierto(terminal_exe):
            return True
    return False


def sqx_databank_identity(sqx_path: Path, sqx_root: Path) -> tuple[str, str, str]:
    """Resolve a candidate's SQX project/databank from its actual path."""
    try:
        relative = sqx_path.resolve().relative_to((sqx_root / "user" / "projects").resolve())
    except ValueError as exc:
        raise ValueError("el .sqx no está dentro de user/projects; no se puede exportar desde su databank SQX") from exc
    parts = relative.parts
    if len(parts) != 4 or parts[1].casefold() != "databanks" or Path(parts[3]).suffix.casefold() != ".sqx":
        raise ValueError("ruta .sqx no reconocida; se esperaba user/projects/<project>/databanks/<databank>/<strategy>.sqx")
    return parts[0], parts[2], Path(parts[3]).stem


def export_sqx_trade_list(
    *, sqx_path: Path, sqx_root: Path, symbol: str, timeframe: str, output_path: Path,
    api_url: str, timeout_s: float = 60,
) -> dict[str, Any]:
    """Ask SQX's native trade-list export endpoint for the full L+S CSV."""
    project, databank, strategy = sqx_databank_identity(sqx_path, sqx_root)
    base = api_url.rstrip("/")
    parsed_base = urllib.parse.urlsplit(base)
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.hostname:
        raise ValueError("SQX_API_URL debe ser una URL HTTP(S) válida")
    if parsed_base.username or parsed_base.password or parsed_base.query or parsed_base.fragment:
        raise ValueError("SQX_API_URL no puede incluir credenciales, query ni fragmento; no se sellan secretos en el manifiesto")
    route = "/tradelist/{}/{}/{}/export".format(*(urllib.parse.quote(part, safe="") for part in (project, databank, strategy)))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_key = f"Main: {symbol}/{timeframe}"
    form = urllib.parse.urlencode({
        "resultKey": result_key,
        "direction": "0",       # SQX constants: both directions
        "sampleType": "127",    # SQX constants: full sample
        "path": str(output_path.resolve()),
        "useComma": "false",    # SQX UI default; semicolon-delimited CSV
    }).encode("utf-8")
    request = urllib.request.Request(
        base + route,
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"falló la exportación nativa de List of Trades en SQX ({base}): {exc}") from exc
    if not isinstance(payload, dict) or payload.get("success") != "Tradelist exported.":
        raise ValueError(f"SQX no confirmó la exportación de List of Trades: {payload!r}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise ValueError("SQX confirmó la exportación pero no creó un CSV no vacío")
    try:
        rows = list(csv.reader(io.StringIO(output_path.read_text(encoding="utf-8-sig")), delimiter=";"))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"no se pudo validar el CSV de List of Trades: {exc}") from exc
    if not rows:
        raise ValueError("el CSV exportado por SQX no contiene cabecera")
    header = {column.strip() for column in rows[0]}
    required = {"Open time", "Close time", "Profit/Loss", "Size"}
    has_costs = "Comm/Swap" in header or {"Commission", "Swap"} <= header
    if not required <= header or not has_costs:
        raise ValueError(f"CSV de SQX sin columnas requeridas de trades/costes: {sorted(header)}")
    if len(rows) < 2:
        raise ValueError("SQX exportó una lista de trades sin operaciones")
    return {
        "path": str(output_path.resolve()),
        "sha256": sha256_file(output_path),
        "project": project,
        "databank": databank,
        "strategy": strategy,
        "result_key": result_key,
        "direction": "BOTH",
        "sample_type": "FULL",
        "cost_column": "Comm/Swap" if "Comm/Swap" in header else "SEPARATE_COMPONENTS",
        "trade_rows": len(rows) - 1,
        "endpoint": base + route,
    }


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
        help="CSV de operaciones SQX ya exportado; si se omite, se obtiene de List of Trades automáticamente.",
    )
    parser.add_argument(
        "--sqx-api-url", default=os.environ.get("SQX_API_URL", "http://127.0.0.1:8080"),
        help="Base URL local de SQX Remote Access (por defecto env SQX_API_URL o http://127.0.0.1:8080).",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-terminal", required=True)
    parser.add_argument("--from", dest="since", help="Por defecto usa dateFrom del .sqx")
    parser.add_argument("--to", dest="until", help="Por defecto usa dateTo del .sqx")
    parser.add_argument("--allow-real-strategy-tester", action="store_true")
    parser.add_argument(
        "--manage-backtest-terminal",
        action="store_true",
        help="Solicita el cierre limpio de la instancia objetivo antes del Tester.",
    )
    parser.add_argument("--launch", action="store_true", help="Ejecuta MT5; por defecto sólo preflight.")
    parser.add_argument(
        "--skip-swap-live-check",
        action="store_true",
        help=(
            "Omite el cross-check en vivo del swap contra MT5/Darwinex (G13-69). Usar solo "
            "cuando ya se ha verificado aparte en la misma sesión operativa: G13-72 documenta "
            "que abrir el terminal para esta consulta puede dejarlo sin poder cerrarse por "
            "automatización una vez conectado a la cuenta en vivo, exigiendo cierre manual del "
            "operador cada vez. Queda registrado en el manifiesto sellado "
            "(swap_live_check_skipped=true), nunca en silencio."
        ),
    )
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

    # Cost-model comparability is independent of the aggregate performance
    # verdict. Preserve its source-backed audit in the same sealed run manifest.
    cost_gate_dir = panel_dir.parent / "capa2_candidate_selector"
    if not (cost_gate_dir / "cost_gate.py").is_file():
        raise SystemExit("falta el gate de costes Capa2; se bloquea la corrida auditable")
    sys.path.insert(0, str(cost_gate_dir))
    from cost_gate import (  # noqa: PLC0415
        build_audit as build_cost_audit,
        cross_validate_swap_against_live_sources,
        finalize_with_empirical_observation,
        sqx_cost_setup,
    )

    cfg = config.cargar(forzar=True)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + sha256_file(sqx_path)[:12]
    output_dir = args.output_root.resolve() / run_id
    terminal = config.terminal(cfg, "terminal_backtest")
    try:
        # Discover and inspect-only preflight is safe even when the configured
        # tester terminal is the user's real-account installation. The explicit
        # flag is required only for an actual Strategy Tester launch.
        assert_safe_terminal(
            terminal, args.expected_terminal,
            args.allow_real_strategy_tester or not args.launch,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    # G13-67 costo la corrida real de AUDCAD: el swap horneado en el .sqx llevaba
    # meses invertido de signo y ~8x infravalorado en data.db sin que nada lo
    # detectara antes de gastar horas en el Tester real. Validarlo en vivo contra
    # MT5 + la web publica de Darwinex (economia.py/darwinex.py) solo tiene
    # sentido para un lanzamiento real -- el preflight nunca debe tocar el
    # terminal (comentario de `aplicar_config` mas abajo).
    #
    # G13-72: abrir un terminal solo para esta consulta y despues cerrarlo por
    # automatizacion resulto no ser fiable -- ni CloseMainWindow() por
    # PowerShell (con reintentos, G13-68), ni una pulsacion sintetica real de
    # Alt+F4 ni un clic real en su boton de cierre (Windows-MCP) cerraron una
    # instancia ya conectada del todo a la cuenta real, probado varias veces en
    # la corrida real del 2026-09-27; solo un cierre manual del operador
    # funciono. Ningun otro modulo del proyecto intenta cerrar un terminal MT5
    # por automatizacion -- compare_sqx_vs_mt5.py lo dice explicitamente
    # ("nunca se cierra ningun proceso desde aqui") y confia en el autocierre
    # de MT5 tras un Tester por /config, o exige que el operador lo cierre a
    # mano si esta abierto; mt5-connector solo llama a mt5.shutdown() (la
    # sesion de la API, nunca la ventana). Este bloque sigue ese mismo patron:
    # solo hace la consulta si el terminal YA estaba abierto por el operador
    # (por otra razon), y nunca lo abre ni lo cierra por su cuenta. El cierre
    # obligatorio antes del Tester real (bloque de --manage-backtest-terminal,
    # justo debajo) se aplica DESPUES de esta consulta oportunista y cubre
    # tanto el caso "ya estaba abierto de antes" como "sigue abierto tras la
    # consulta".
    swap_live_check = None
    if args.launch and not args.skip_swap_live_check:
        try:
            sqx_swap_setup = sqx_cost_setup(sqx_path)
        except (OSError, ValueError) as exc:
            raise SystemExit(f"no se pudo leer el swap SQX para la validación en vivo; queda WITHHELD: {exc}") from exc
        live_symbol = resolve_symbol_for_ticks(config, cfg, sqx_swap_setup["symbol"])
        if not live_symbol:
            swap_live_check = {
                "state": "unavailable",
                "reason": "no se pudo resolver el símbolo MT5 para la validación en vivo",
            }
        elif not compare.terminal_abierto(terminal["exe"]):
            swap_live_check = {
                "state": "unavailable",
                "reason": (
                    "el terminal MT5 de backtest está cerrado; el cross-check en vivo solo se "
                    "realiza sobre una instancia ya abierta (G13-72), nunca abre ni cierra una "
                    "por su cuenta. Ábralo manualmente antes de lanzar, o use "
                    "--skip-swap-live-check si ya se verificó aparte."
                ),
            }
        else:
            swap_live_check = cross_validate_swap_against_live_sources(
                live_symbol, sqx_swap_setup["swap"], terminal=terminal,
            )

    if args.launch and compare.terminal_abierto(terminal["exe"]):
        if not args.manage_backtest_terminal:
            raise SystemExit("el terminal MT5 de backtest está abierto; use --manage-backtest-terminal autorizado")
        if not close_target_terminal(compare, terminal["exe"]):
            raise SystemExit("MT5 no aceptó el cierre limpio de la instancia de backtest")

    # The official Results > List of Trades export carries cost evidence absent
    # from many .sqx orders.bin files. Keep it beside the run for a reproducible seal.
    export_evidence: dict[str, Any] | None = None
    if not sqx_trades_csv:
        try:
            sqx_context = compare.contexto_sqx_desde_archivo(sqx_path)
            export_evidence = export_sqx_trade_list(
                sqx_path=sqx_path,
                sqx_root=Path(cfg["raiz_sqx"]),
                symbol=sqx_context["simbolo"],
                timeframe=sqx_context["timeframe"],
                output_path=output_dir / "sqx-trades-source.csv",
                api_url=args.sqx_api_url,
            )
            sqx_trades_csv = Path(export_evidence["path"])
        except (OSError, ValueError) as exc:
            raise SystemExit(f"no se pudo obtener evidencia de costes desde SQX; queda WITHHELD: {exc}") from exc

    # El preflight replica las precondiciones de --strict-real-ticks sin compilar
    # ni abrir MT5. Así una cola no deja resultados ambiguos por M1-OHLC.
    compare.aplicar_config(cfg)
    sqx = compare.cargar_lado_sqx(sqx_path, sqx_trades_csv)
    try:
        cost_audit = build_cost_audit(sqx_path, mt5_spread_model="REAL_TICKS", swap_live_check=swap_live_check)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"no se pudo auditar comparabilidad de costes; queda WITHHELD: {exc}") from exc
    sqx_symbol, timeframe = sqx["simbolo"], sqx["timeframe"]
    sqx_cost = cost_audit["cost_comparability"]["sqx"]
    try:
        since, until = resolve_test_range(sqx_cost, args.since, args.until)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if not sqx_symbol or not timeframe:
        raise SystemExit("no se pudo extraer símbolo/timeframe del .sqx; queda WITHHELD")
    symbol = resolve_symbol_for_ticks(config, cfg, sqx_symbol)
    if not symbol:
        raise SystemExit("no hay alias o ticks reales para el símbolo; queda WITHHELD")
    ticks = compare.cobertura_ticks(symbol)
    since_dt, until_dt = compare.parsear_fecha(since), compare.parsear_fecha(until)
    if since_dt is None or until_dt is None or since_dt >= until_dt:
        raise SystemExit("rango de backtest inválido")
    if not ticks or since_dt < ticks[0] or until_dt > ticks[1]:
        raise SystemExit("el rango 2018-actual exige ticks reales completos; queda WITHHELD")

    command = build_command(
        panel_dir=panel_dir,
        sqx_path=sqx_path,
        mq5_path=mq5_path,
        output_dir=output_dir,
        since=since,
        until=until,
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
            "exe": terminal["exe"],
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
            **({"sqx_trade_export": export_evidence} if export_evidence else {}),
        },
        "range": {"from": since, "to": until, "real_ticks_required": True},
        "cost_audit": cost_audit,
        "swap_live_check_skipped": bool(args.skip_swap_live_check),
        "seal_eligible": bool(cost_audit["seal_allowed"]),
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
    observation_path = output_dir / "cost-reconciliation.json"
    if result.returncode == 0 and observation_path.is_file():
        try:
            cost_audit = finalize_with_empirical_observation(
                cost_audit,
                observation_path,
                expected_sqx_sha256=payload["source"]["sqx_sha256"],
                expected_sqx_trades_sha256=payload["source"].get("sqx_trades_csv_sha256"),
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            payload["cost_reconciliation_error"] = str(exc)
        payload["cost_audit"] = cost_audit
        payload["seal_eligible"] = bool(cost_audit["seal_allowed"])
    elif result.returncode == 0:
        payload["cost_reconciliation_error"] = "missing cost-reconciliation.json; cost gate remains blocked"
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
