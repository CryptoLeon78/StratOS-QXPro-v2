"""Genera el perfil local, aislado y read-only del conector para G12."""

from __future__ import annotations

import argparse
from pathlib import Path


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise ValueError(f"línea inválida en {path}: {raw_line!r}")
        values[key] = value
    return values


def build_values(
    g12_env: dict[str, str],
    *,
    account_login: str,
    terminal_exe: Path,
    terminal_data_root: Path,
    runtime_root: Path | None = None,
) -> dict[str, str]:
    ingest_key = g12_env.get("INGEST_API_KEYS", "")
    if not ingest_key or "," in ingest_key:
        raise ValueError("G12 requiere exactamente una INGEST_API_KEYS aislada")
    core_port = g12_env.get("G12_CORE_PORT", "8200")
    common_files = terminal_data_root.parent / "Common" / "Files"
    buffer_path = (
        runtime_root / "runtime" / "g12" / "connector-buffer.sqlite"
        if runtime_root is not None
        else Path("runtime") / "g12" / "connector-buffer.sqlite"
    )
    return {
        "CONNECTOR_CORE_ENGINE_URL": f"http://127.0.0.1:{core_port}",
        "CONNECTOR_INGEST_API_KEY": ingest_key,
        "CONNECTOR_ACCOUNT_LOGIN": account_login,
        "CONNECTOR_BUFFER_DB_PATH": str(buffer_path),
        "CONNECTOR_REPORTER_OUTBOX_DIR": str(common_files),
        "CONNECTOR_REPORTER_OUTBOX_FILENAME": "stratos_g12_*.jsonl",
        "CONNECTOR_MT5_TERMINAL_PATH": str(terminal_exe),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g12-env", type=Path, default=Path(".env.g12"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--terminal-exe", type=Path, required=True)
    parser.add_argument("--terminal-data-root", type=Path, required=True)
    args = parser.parse_args()

    if not args.terminal_exe.is_file():
        raise ValueError(f"no existe el ejecutable MT5 demo: {args.terminal_exe}")
    if not args.terminal_data_root.is_dir():
        raise ValueError(f"no existe el data root MT5 demo: {args.terminal_data_root}")
    values = build_values(
        read_env(args.g12_env),
        account_login=args.account_login,
        terminal_exe=args.terminal_exe,
        terminal_data_root=args.terminal_data_root,
        runtime_root=args.g12_env.parent.resolve(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()) + "\n",
        encoding="utf-8",
    )
    print(
        "Perfil de conector G12 generado (sin exponer claves): "
        f"core={values['CONNECTOR_CORE_ENGINE_URL']}, outbox={values['CONNECTOR_REPORTER_OUTBOX_DIR']}, "
        f"archivo={values['CONNECTOR_REPORTER_OUTBOX_FILENAME']}"
    )


if __name__ == "__main__":
    main()
