"""PARTE 10.1 (extendido a G4): configuracion de despliegue del conector --
deployable propio, separado de `core-engine`. Vive en su propio `.env`
(`mt5-connector/.env`, junto a su `pyproject.toml`), nunca en el `.env` de
la raiz del repo: en produccion este paquete se instala solo en un VPS
Windows, sin el resto del monorepo necesariamente presente (PARTE 3).

Solo `positions_poll_interval_s=5`/`equity_poll_interval_s=30`/
`heartbeat_interval_s=60`/`backoff_max_seconds=300` son literales de PARTE
12 (G4). `deals_poll_interval_s` y `backoff_base_seconds`/
`backoff_multiplier` son asuncion propia (ASSUMPTIONS G4) -- el prompt
maestro no da esos numeros."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONNECTOR_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class ConnectorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONNECTOR_", env_file=_CONNECTOR_ENV_FILE, extra="ignore"
    )

    core_engine_url: str
    ingest_api_key: str
    account_login: str

    positions_poll_interval_s: float = 5.0
    deals_poll_interval_s: float = 5.0
    equity_poll_interval_s: float = 30.0
    heartbeat_interval_s: float = 60.0

    backoff_base_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    backoff_max_seconds: float = 300.0

    buffer_db_path: str = Field(default=r"C:\ProgramData\StratOSQXPro\mt5-connector\buffer.sqlite")
    reporter_outbox_dir: str | None = None
    reporter_outbox_filename: str = "*.jsonl"
    mt5_terminal_path: str | None = None

    @field_validator("reporter_outbox_filename")
    @classmethod
    def reporter_outbox_filename_is_local(cls, value: str) -> str:
        if not value or Path(value).name != value:
            raise ValueError("reporter_outbox_filename debe ser un patrón de archivo local")
        return value


@lru_cache
def get_connector_settings() -> ConnectorSettings:
    return ConnectorSettings()  # type: ignore[call-arg]
