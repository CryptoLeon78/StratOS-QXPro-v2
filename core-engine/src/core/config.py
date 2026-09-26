from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resuelto contra la raiz del repo, no contra el cwd: pytest corre con
# cwd=core-engine (testpaths=["tests"]) y ".env" relativo no lo encontraria
# ahi (bug real encontrado al montar los fixtures de tests de G1).
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """PARTE 10.1: unica fuente de configuracion de despliegue (env). Nada de
    URLs, credenciales ni TTLs hardcodeados en logica de negocio."""

    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV_FILE, extra="ignore")

    database_url: str = Field(validation_alias="DATABASE_URL")
    app_database_url: str = Field(validation_alias="APP_DATABASE_URL")
    # Solo la usa la migracion 0001 para crear el rol stratos_app (CREATE
    # ROLE ... PASSWORD); no se usa en runtime de la app.
    app_db_password: str = Field(validation_alias="APP_DB_PASSWORD")
    # Dimensionado del pool de conexiones. El default implicito de SQLAlchemy
    # (5 + 10) no cubre un despliegue que recibe telemetria continua de varias
    # cuentas mientras el operador usa la UI: la ingesta agota las conexiones y
    # el login deja de responder. Es un parametro de despliegue, no de negocio.
    db_pool_size: int = Field(default=20, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    redis_url: str = Field(validation_alias="REDIS_URL")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_access_ttl_min: int = Field(default=15, validation_alias="JWT_ACCESS_TTL_MIN")
    jwt_refresh_ttl_days: int = Field(default=30, validation_alias="JWT_REFRESH_TTL_DAYS")

    ingest_api_keys: str = Field(validation_alias="INGEST_API_KEYS")

    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", validation_alias="TELEGRAM_CHAT_ID")
    # Lista opcional de destinos, separada por comas. Cuando se define, tiene
    # prioridad sobre el destino unico heredado para permitir alertas a varios
    # grupos sin duplicar procesos de notificacion.
    telegram_chat_ids: str = Field(default="", validation_alias="TELEGRAM_CHAT_IDS")
    telegram_recovery_chat_id: str = Field(
        default="", validation_alias="TELEGRAM_RECOVERY_CHAT_ID"
    )

    sentry_dsn: str = Field(default="", validation_alias="SENTRY_DSN")

    deployment_profile: str = Field(default="full", validation_alias="DEPLOYMENT_PROFILE")
    tz_display: str = Field(default="Europe/Madrid", validation_alias="TZ_DISPLAY")
    base_currency: str = Field(default="EUR", validation_alias="BASE_CURRENCY")
    # Sólo lectura: el lanzador Windows publica aquí la vista sellada de su
    # cola. El core nunca recibe permiso para ejecutar el terminal local.
    operational_runtime_dir: Path = Field(
        default=Path("/runtime"), validation_alias="OPERATIONAL_RUNTIME_DIR"
    )
    pipeline_agent_api_key: str = Field(default="", validation_alias="PIPELINE_AGENT_API_KEY")

    news_provider: str = Field(default="ics", validation_alias="NEWS_PROVIDER")
    news_source_url: str = Field(default="", validation_alias="NEWS_SOURCE_URL")
    benchmark_provider: str = Field(default="csv", validation_alias="BENCHMARK_PROVIDER")
    benchmark_symbol: str = Field(default="^SPX", validation_alias="BENCHMARK_SYMBOL")
    # G10 (docs/backlog.md): benchmark_provider="csv" ya estaba declarado
    # desde G0/G1 sin que nada lo consumiera -- services/benchmark.py es el
    # primer consumidor real. None (default) -> el servicio resuelve la
    # ruta contra la raiz del repo (mismo criterio que _REPO_ROOT_ENV_FILE);
    # Path | None en vez de una ruta ya resuelta como default para que un
    # BENCHMARK_CSV_PATH vacio en .env no se coerciones a Path(""), que
    # apuntaria al cwd en vez de caer al default real.
    benchmark_csv_path: Path | None = Field(default=None, validation_alias="BENCHMARK_CSV_PATH")

    operator_email: str = Field(default="", validation_alias="OPERATOR_EMAIL")
    operator_password_hash: str = Field(default="", validation_alias="OPERATOR_PASSWORD_HASH")
    auth_recovery_code_ttl_s: int = Field(default=600, validation_alias="AUTH_RECOVERY_CODE_TTL_S")
    auth_recovery_code_length: int = Field(default=6, validation_alias="AUTH_RECOVERY_CODE_LENGTH")
    auth_recovery_max_attempts: int = Field(default=5, validation_alias="AUTH_RECOVERY_MAX_ATTEMPTS")
    auth_recovery_request_cooldown_s: int = Field(
        default=60, validation_alias="AUTH_RECOVERY_REQUEST_COOLDOWN_S"
    )
    auth_password_min_length: int = Field(
        default=12, validation_alias="AUTH_PASSWORD_MIN_LENGTH"
    )
    auth_recovery_telegram_template: str = Field(
        default="StratOS: tu codigo de recuperacion es {code}. Caduca en {minutes} min.",
        validation_alias="AUTH_RECOVERY_TELEGRAM_TEMPLATE",
    )

    # No esta en la lista literal de PARTE 10.1 (escrita antes de que G6
    # decidiera que el frontend habla DIRECTO con core-engine, sin
    # api-gateway de por medio -- ASSUMPTIONS G6-00). Sin esto, el navegador
    # bloquea toda peticion desde el dev server de Vite (origen distinto).
    # :5175 (ademas de :5173): puerto que usa el harness Playwright de G8
    # (`frontend/playwright.config.ts`, deliberadamente distinto de :5173
    # para no chocar con una instancia de `npm run dev` ya abierta) -- bug
    # real encontrado en G8: sin este origen, todo login/fetch del harness
    # E2E fallaba por CORS (enmascarado en la UI como "credenciales
    # incorrectas", ver ASSUMPTIONS G8).
    cors_allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:5175",
        validation_alias="CORS_ALLOWED_ORIGINS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
