"""Construye un perfil MT5 aislado para adjuntar los EAs G12 READY en MetaQuotes-Demo.

El script no envía órdenes.  Sólo materializa los ficheros de perfil de MT5 y,
de forma opcional, valida el terminal demo que ya está conectado.  La carga de
los EAs la realiza MT5 al abrir el perfil; sus órdenes, si las hubiera, proceden
del código de los EAs y se limitan a la cuenta demo indicada por el usuario.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


TIMEFRAME_TO_PERIOD: dict[str, tuple[int, int]] = {
    "M1": (1, 1),
    "M5": (1, 5),
    "M15": (1, 15),
    "M30": (0, 30),
    "H1": (1, 1),
    "H4": (1, 4),
    "D1": (1, 24),
}
EXPECTED_READY_COUNT = 11
MAGIC_INPUT = re.compile(r"input\s+int\s+MagicNumber\s*=\s*(\d+)\s*;")
REPORTER_VERSION_INPUT = re.compile(r'input\s+string\s+StratosReporterVersion\s*=\s*"([^"]+)"\s*;')
REPORTER_OUTBOX_INPUT = re.compile(r'input\s+string\s+StratosReporterOutbox\s*=\s*"([^"]+)"\s*;')


@dataclass(frozen=True)
class Attachment:
    chart_file: str
    strategy_name: str
    magic_number: int
    sqx_symbol: str
    mt5_symbol: str
    timeframe: str
    expert_relative_path: str
    reporter_outbox: str
    operational_mode: str
    sizing_pct: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_utf16(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-16")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_profile_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", value):
        raise ValueError("--profile-name sólo admite letras, números, punto, guion y guion bajo")
    return value


def _ready_candidates(manifest: dict[str, Any], allow_withheld: bool) -> list[dict[str, Any]]:
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("manifest inválido: falta candidates")
    ready = [item for item in candidates if item.get("status") == "READY"]
    withheld = [item for item in candidates if item.get("status") != "READY"]
    if withheld and not allow_withheld:
        raise ValueError("el manifest contiene candidatos retenidos; exige --allow-withheld")
    if len(ready) != EXPECTED_READY_COUNT:
        raise ValueError(f"se esperaban {EXPECTED_READY_COUNT} READY y se encontraron {len(ready)}")
    return ready


def _validate_source(source_path: Path, magic_number: int, reporter_version: str) -> str:
    if not source_path.is_file():
        raise ValueError(f"falta fuente instrumentada: {source_path}")
    source = source_path.read_text(encoding="utf-8", errors="ignore")
    found_magic = MAGIC_INPUT.search(source)
    found_version = REPORTER_VERSION_INPUT.search(source)
    found_outbox = REPORTER_OUTBOX_INPUT.search(source)
    expected_outbox = f"stratos_g12_{magic_number}.jsonl"
    if not found_magic or int(found_magic.group(1)) != magic_number:
        raise ValueError(f"MagicNumber no coincide en {source_path.name}")
    if not found_version or found_version.group(1) != reporter_version:
        raise ValueError(f"versión reporter no coincide en {source_path.name}")
    if not found_outbox or found_outbox.group(1) != expected_outbox:
        raise ValueError(f"outbox reporter no coincide en {source_path.name}")
    if "StratosReporterManagedOnInit" not in source or "StratosReporterManagedOnTradeTransaction" not in source:
        raise ValueError(f"callbacks reporter incompletos en {source_path.name}")
    return expected_outbox


def build_attachments(
    manifest: dict[str, Any], terminal_data_root: Path, symbol_map: dict[str, str], allow_withheld: bool,
    operational_mode: str, sizing_pct: str,
) -> list[Attachment]:
    reporter_version = str(manifest.get("ea_required_version") or "")
    if not reporter_version:
        raise ValueError("manifest inválido: falta ea_required_version")
    attachments: list[Attachment] = []
    used_magics: set[int] = set()
    experts_dir = terminal_data_root / "MQL5" / "Experts" / "StratOS_G12"
    for index, candidate in enumerate(_ready_candidates(manifest, allow_withheld), start=1):
        strategy_name = str(candidate["strategy_name"])
        magic_number = int(candidate["magic_number"])
        sqx_symbol = str(candidate.get("darwinex_symbol") or candidate.get("sqx", {}).get("symbol") or "")
        timeframe = str(candidate["timeframe"]).upper()
        if magic_number in used_magics:
            raise ValueError(f"MagicNumber duplicado: {magic_number}")
        if timeframe not in TIMEFRAME_TO_PERIOD:
            raise ValueError(f"timeframe no soportado para {strategy_name}: {timeframe}")
        if not sqx_symbol or sqx_symbol not in symbol_map or not symbol_map[sqx_symbol]:
            raise ValueError(f"falta mapeo MT5 explícito para {sqx_symbol or strategy_name}")
        source_path = experts_dir / f"{strategy_name}.mq5"
        compiled_path = experts_dir / f"{strategy_name}.ex5"
        reporter_outbox = _validate_source(source_path, magic_number, reporter_version)
        if not compiled_path.is_file():
            raise ValueError(f"falta binario compilado: {compiled_path}")
        if compiled_path.stat().st_mtime < source_path.stat().st_mtime:
            raise ValueError(f"binario anterior al fuente: {compiled_path.name}")
        used_magics.add(magic_number)
        attachments.append(
            Attachment(
                chart_file=f"chart{index:02d}.chr",
                strategy_name=strategy_name,
                magic_number=magic_number,
                sqx_symbol=sqx_symbol,
                mt5_symbol=str(symbol_map[sqx_symbol]),
                timeframe=timeframe,
                expert_relative_path=f"Experts\\StratOS_G12\\{strategy_name}.ex5",
                reporter_outbox=reporter_outbox,
                operational_mode=operational_mode,
                sizing_pct=sizing_pct,
            )
        )
    return attachments


def chart_text(attachment: Attachment, chart_id: int) -> str:
    period_type, period_size = TIMEFRAME_TO_PERIOD[attachment.timeframe]
    return f"""<chart>
id={chart_id}
symbol={attachment.mt5_symbol}
description=StratOS G12 demo {attachment.magic_number}
period_type={period_type}
period_size={period_size}
digits=5
tick_size=0.000000
position_time=0
scale_fix=0
scale_fixed_min=0.000000
scale_fixed_max=0.000000
scale_fix11=0
scale_bar=0
scale_bar_val=0.000000
scale=4
mode=1
fore=0
grid=1
volume=0
scroll=1
shift=1
shift_size=20.000000
fixed_pos=0.000000
ohlc=0
bidline=1
askline=0
lastline=0
days=0
descriptions=0
window_type=1
background_color=0
foreground_color=16777215
barup_color=65280
bardown_color=65280
bullcandle_color=0
bearcandle_color=16777215
chartline_color=65280
volumes_color=3329330
grid_color=10061943
bidline_color=10061943
askline_color=255
lastline_color=49152
stops_color=255
windows_total=1

<expert>
name={attachment.strategy_name}
path={attachment.expert_relative_path}
expertmode={1 if attachment.operational_mode == "REAL" else 0}
<inputs>
MagicNumber={attachment.magic_number}
StratosReporterVersion=g12-reporter-v1.1
StratosReporterEnabled=true
StratosReporterOutbox={attachment.reporter_outbox}
StratosReporterOperationalMode={attachment.operational_mode}
StratosReporterSizingPct={attachment.sizing_pct}
</inputs>
</expert>

<window>
height=100
<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
</indicator>
</window>
</chart>
"""


def _profile_files(attachments: list[Attachment], profile_name: str) -> dict[str, str]:
    files = {attachment.chart_file: chart_text(attachment, 128968171281015625 + index) for index, attachment in enumerate(attachments)}
    files["order.wnd"] = "\n".join(attachment.chart_file for attachment in attachments) + "\n"
    return files


def write_profile(
    attachments: list[Attachment], terminal_data_root: Path, profile_name: str,
    resume: bool, replace_profile: bool,
) -> Path:
    profile_dir = terminal_data_root / "MQL5" / "Profiles" / "Charts" / profile_name
    expected = _profile_files(attachments, profile_name)
    if profile_dir.exists():
        if not resume:
            raise ValueError(f"perfil ya existe: {profile_dir}; usar --resume o --replace-profile")
        actual = {path.name: path.read_text(encoding="utf-16") for path in profile_dir.iterdir() if path.is_file()}
        if actual != expected:
            if not replace_profile:
                raise ValueError(f"perfil existente distinto: {profile_dir}; no se sobrescribe")
            backup_dir = profile_dir.with_name(f"{profile_name}.backup")
            if backup_dir.exists():
                raise ValueError(f"ya existe la copia de seguridad: {backup_dir}")
            shutil.copytree(profile_dir, backup_dir)
            shutil.rmtree(profile_dir)
        else:
            return profile_dir
    profile_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{profile_name}-", dir=profile_dir.parent) as staging:
        staging_path = Path(staging)
        for filename, contents in expected.items():
            _write_utf16(staging_path / filename, contents)
        staging_path.rename(profile_dir)
    return profile_dir


def validate_live_terminal(terminal_exe: Path, terminal_data_root: Path, attachments: list[Attachment]) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:  # pragma: no cover - depende del host MT5
        raise RuntimeError("MetaTrader5 no está instalado; omite --verify-live-terminal o usa el venv del connector") from exc
    if not mt5.initialize(path=str(terminal_exe)):
        raise RuntimeError(f"no se pudo inicializar MetaTrader5: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise RuntimeError("MT5 no devolvió terminal/account info")
        data_path = Path(str(terminal.data_path)).resolve()
        if data_path != terminal_data_root.resolve():
            raise RuntimeError("el terminal activo no usa el terminal-data-root indicado")
        if str(account.server) != "MetaQuotes-Demo":
            raise RuntimeError("el terminal activo no es MetaQuotes-Demo")
        symbol_status: dict[str, dict[str, Any]] = {}
        for symbol in sorted({item.mt5_symbol for item in attachments}):
            info = mt5.symbol_info(symbol)
            if info is None or not info.visible:
                raise RuntimeError(f"símbolo no disponible/visible en MetaQuotes-Demo: {symbol}")
            symbol_status[symbol] = {"visible": bool(info.visible), "trade_mode": int(info.trade_mode)}
        return {
            "terminal_data_root_matches": True,
            "server": "MetaQuotes-Demo",
            "terminal_trade_allowed": bool(terminal.trade_allowed),
            "account_trade_expert": bool(account.trade_expert),
            "symbols": symbol_status,
        }
    finally:
        mt5.shutdown()


def attach(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = _safe_profile_name(args.profile_name)
    manifest = _read_json(args.manifest)
    symbol_map = _read_json(args.symbol_map)
    if not isinstance(symbol_map, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in symbol_map.items()):
        raise ValueError("--symbol-map debe ser un objeto JSON string:string")
    attachments = build_attachments(
        manifest, args.terminal_data_root, symbol_map, args.allow_withheld,
        args.operational_mode, args.sizing_pct,
    )
    live = validate_live_terminal(args.terminal_exe, args.terminal_data_root, attachments) if args.verify_live_terminal else None
    profile_dir = args.terminal_data_root / "MQL5" / "Profiles" / "Charts" / profile_name
    if args.apply:
        profile_dir = write_profile(
            attachments, args.terminal_data_root, profile_name, args.resume, args.replace_profile
        )
    payload = {
        "ok": True,
        "mode": "apply" if args.apply else "dry_run",
        "terminal_exe": str(args.terminal_exe),
        "terminal_data_root": str(args.terminal_data_root),
        "profile_name": profile_name,
        "profile_dir": str(profile_dir),
        "launch_args": [f"/profile:{profile_name}"],
        "ready_count": len(attachments),
        "withheld_count": len([item for item in manifest["candidates"] if item.get("status") != "READY"]),
        "attachments": [asdict(item) for item in attachments],
        "compiled_sha256": {
            item.strategy_name: _sha256(args.terminal_data_root / "MQL5" / "Experts" / "StratOS_G12" / f"{item.strategy_name}.ex5")
            for item in attachments
        },
        "live_validation": live,
        "next_action": "use scripts/launch_g12_demo_profile.ps1 -Restart; it closes only the exact demo terminal and launches /profile:<profile_name>",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--terminal-exe", required=True, type=Path)
    parser.add_argument("--terminal-data-root", required=True, type=Path)
    parser.add_argument("--symbol-map", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--profile-name", default="StratOS_G12_Demo_11Ready")
    parser.add_argument("--allow-withheld", action="store_true")
    parser.add_argument("--operational-mode", choices=("PAPER", "REAL"), required=True)
    parser.add_argument("--sizing-pct", required=True)
    parser.add_argument("--verify-live-terminal", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--replace-profile", action="store_true")
    return parser.parse_args()


def main() -> None:
    payload = attach(parse_args())
    print(f"G12 MT5: {payload['ready_count']} EAs READY validados; modo={payload['mode']}; perfil={payload['profile_name']}")


if __name__ == "__main__":
    main()
