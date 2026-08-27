from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Mismo criterio que core-engine/src/core/config.py: resuelto contra la raiz
# del repo, no contra el cwd, para que Alembic/pytest/uvicorn encuentren el
# mismo .env sin importar desde donde se invoquen.
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """PARTE 10.1/G9: configuracion de despliegue del gateway. El gateway no
    tiene JWT_SECRET propio -- nunca valida el token el mismo, solo lo
    reenvia intacto a core-engine (unica fuente de verdad de auth, ver
    ASSUMPTIONS G9)."""

    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV_FILE, extra="ignore")

    core_engine_url: str = Field(
        default="http://localhost:8100", validation_alias="CORE_ENGINE_URL"
    )
    core_engine_ws_url: str = Field(
        default="ws://localhost:8100", validation_alias="CORE_ENGINE_WS_URL"
    )
    redis_url: str = Field(validation_alias="REDIS_URL")
    rate_limit_per_minute: int = Field(default=120, validation_alias="RATE_LIMIT_PER_MINUTE")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
