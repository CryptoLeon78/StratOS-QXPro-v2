"""Crea el entorno local e ignorado de G12 sin tocar .env ni G11."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path


REQUIRED_SOURCE_KEYS = ("JWT_SECRET", "OPERATOR_EMAIL", "OPERATOR_PASSWORD_HASH")
G12_PORTS = {
    "G12_POSTGRES_PORT": "56432",
    "G12_REDIS_PORT": "6480",
    "G12_CORE_PORT": "8200",
    "G12_GATEWAY_PORT": "8280",
    "G12_FRONTEND_PORT": "5373",
}


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


# Bytes de entropia por secreto generado. No es un umbral de negocio: es el tamano de
# `secrets.token_urlsafe`, que produce ~43 caracteres url-safe por cada 32 bytes.
SECRET_TOKEN_BYTES = 32


def build_g12_env(source: dict[str, str]) -> dict[str, str]:
    missing = [key for key in REQUIRED_SOURCE_KEYS if not source.get(key)]
    if missing:
        raise ValueError(f".env origen incompleto: faltan {', '.join(missing)}")
    postgres_password = secrets.token_urlsafe(SECRET_TOKEN_BYTES)
    app_password = secrets.token_urlsafe(SECRET_TOKEN_BYTES)
    ingest_key = secrets.token_urlsafe(SECRET_TOKEN_BYTES)
    values = {
        "POSTGRES_DB": "stratos_g12",
        "POSTGRES_USER": "stratos_g12_user",
        "POSTGRES_PASSWORD": postgres_password,
        "APP_DB_PASSWORD": app_password,
        "DATABASE_URL": f"postgresql+asyncpg://stratos_g12_user:{postgres_password}@localhost:56432/stratos_g12",
        "APP_DATABASE_URL": f"postgresql+asyncpg://stratos_app:{app_password}@localhost:56432/stratos_g12",
        "REDIS_URL": "redis://localhost:6480/0",
        "JWT_SECRET": source["JWT_SECRET"],
        "JWT_ACCESS_TTL_MIN": source.get("JWT_ACCESS_TTL_MIN", "15"),
        "JWT_REFRESH_TTL_DAYS": source.get("JWT_REFRESH_TTL_DAYS", "30"),
        "INGEST_API_KEYS": ingest_key,
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
        "SENTRY_DSN": "",
        "DEPLOYMENT_PROFILE": "full",
        "TZ_DISPLAY": source.get("TZ_DISPLAY", "Europe/Madrid"),
        "BASE_CURRENCY": source.get("BASE_CURRENCY", "EUR"),
        "NEWS_PROVIDER": source.get("NEWS_PROVIDER", "ics"),
        "NEWS_SOURCE_URL": source.get("NEWS_SOURCE_URL", ""),
        "BENCHMARK_PROVIDER": source.get("BENCHMARK_PROVIDER", "csv"),
        "BENCHMARK_SYMBOL": source.get("BENCHMARK_SYMBOL", "^SPX"),
        "OPERATOR_EMAIL": source["OPERATOR_EMAIL"],
        "OPERATOR_PASSWORD_HASH": source["OPERATOR_PASSWORD_HASH"],
        "CORS_ALLOWED_ORIGINS": "http://localhost:5373",
        "CORE_ENGINE_URL": "http://localhost:8200",
        "CORE_ENGINE_WS_URL": "ws://localhost:8200",
        "RATE_LIMIT_PER_MINUTE": source.get("RATE_LIMIT_PER_MINUTE", "120"),
        "BACKUP_RETENTION_DAYS": source.get("BACKUP_RETENTION_DAYS", "14"),
        **G12_PORTS,
    }
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path, default=Path(".env.g12"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"{args.output} ya existe; se conserva. Usa --force solo para recrearlo.")
    values = build_g12_env(_read_env(args.source))
    args.output.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")
    print(f"Entorno G12 creado en {args.output}; contiene secretos y está ignorado por git.")


if __name__ == "__main__":
    main()
