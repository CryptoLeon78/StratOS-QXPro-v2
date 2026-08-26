"""ConnectorSettings: defaults de cadencia/backoff (PARTE 12 + asunciones
propias, ver ASSUMPTIONS G4), prefijo de entorno CONNECTOR_."""

import pytest

from connector.config import ConnectorSettings, get_connector_settings


def test_defaults_match_parte_12_contractual_values() -> None:
    settings = ConnectorSettings(
        core_engine_url="https://core.example.com",
        ingest_api_key="key",
        account_login="100231",
    )
    assert settings.positions_poll_interval_s == 5.0
    assert settings.equity_poll_interval_s == 30.0
    assert settings.heartbeat_interval_s == 60.0
    assert settings.backoff_max_seconds == 300.0


def test_deals_and_backoff_base_are_the_documented_assumption() -> None:
    settings = ConnectorSettings(
        core_engine_url="https://core.example.com",
        ingest_api_key="key",
        account_login="100231",
    )
    assert settings.deals_poll_interval_s == 5.0
    assert settings.backoff_base_seconds == 5.0
    assert settings.backoff_multiplier == 2.0


def test_get_connector_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONNECTOR_CORE_ENGINE_URL", "https://cached.example.com")
    monkeypatch.setenv("CONNECTOR_INGEST_API_KEY", "cachedkey")
    monkeypatch.setenv("CONNECTOR_ACCOUNT_LOGIN", "111")
    get_connector_settings.cache_clear()
    settings = get_connector_settings()
    assert settings.core_engine_url == "https://cached.example.com"
    get_connector_settings.cache_clear()


def test_env_prefix_is_connector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONNECTOR_CORE_ENGINE_URL", "https://x.example.com")
    monkeypatch.setenv("CONNECTOR_INGEST_API_KEY", "envkey")
    monkeypatch.setenv("CONNECTOR_ACCOUNT_LOGIN", "999")
    settings = ConnectorSettings()
    assert settings.core_engine_url == "https://x.example.com"
    assert settings.ingest_api_key == "envkey"
    assert settings.account_login == "999"
