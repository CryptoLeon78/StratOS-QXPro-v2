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
    redis_url: str = Field(validation_alias="REDIS_URL")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_access_ttl_min: int = Field(default=15, validation_alias="JWT_ACCESS_TTL_MIN")
    jwt_refresh_ttl_days: int = Field(default=30, validation_alias="JWT_REFRESH_TTL_DAYS")

    ingest_api_keys: str = Field(validation_alias="INGEST_API_KEYS")

    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", validation_alias="TELEGRAM_CHAT_ID")

    sentry_dsn: str = Field(default="", validation_alias="SENTRY_DSN")

    deployment_profile: str = Field(default="full", validation_alias="DEPLOYMENT_PROFILE")
    tz_display: str = Field(default="Europe/Madrid", validation_alias="TZ_DISPLAY")
    base_currency: str = Field(default="EUR", validation_alias="BASE_CURRENCY")

    news_provider: str = Field(default="ics", validation_alias="NEWS_PROVIDER")
    news_source_url: str = Field(default="", validation_alias="NEWS_SOURCE_URL")
    benchmark_provider: str = Field(default="csv", validation_alias="BENCHMARK_PROVIDER")
    benchmark_symbol: str = Field(default="^SPX", validation_alias="BENCHMARK_SYMBOL")

    operator_email: str = Field(default="", validation_alias="OPERATOR_EMAIL")
    operator_password_hash: str = Field(default="", validation_alias="OPERATOR_PASSWORD_HASH")

    # No esta en la lista literal de PARTE 10.1 (escrita antes de que G6
    # decidiera que el frontend habla DIRECTO con core-engine, sin
    # api-gateway de por medio -- ASSUMPTIONS G6-00). Sin esto, el navegador
    # bloquea toda peticion desde el dev server de Vite (origen distinto).
    cors_allowed_origins: str = Field(
        default="http://localhost:5173", validation_alias="CORS_ALLOWED_ORIGINS"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
