from __future__ import annotations

from pathlib import Path

import pytest

from scripts.create_g12_connector_env import build_values


def test_g12_connector_profile_isolated_and_scoped_to_its_own_outbox() -> None:
    values = build_values(
        {"INGEST_API_KEYS": "g12-ingest-key", "G12_CORE_PORT": "8200"},
        account_login="demo-123",
        terminal_exe=Path(r"C:\\Program Files\\MetaTrader 5\\terminal64.exe"),
        terminal_data_root=Path(r"C:\\Users\\Ivan SQX\\AppData\\Roaming\\MetaQuotes\\Terminal\\demo"),
    )

    assert values["CONNECTOR_CORE_ENGINE_URL"] == "http://127.0.0.1:8200"
    assert values["CONNECTOR_REPORTER_OUTBOX_FILENAME"] == "stratos_g12_*.jsonl"
    assert values["CONNECTOR_BUFFER_DB_PATH"] == r"runtime\g12\connector-buffer.sqlite"


def test_g12_connector_profile_uses_an_absolute_buffer_when_runtime_root_is_given(
    tmp_path: Path,
) -> None:
    values = build_values(
        {"INGEST_API_KEYS": "g12-ingest-key", "G12_CORE_PORT": "8200"},
        account_login="demo-123",
        terminal_exe=Path(r"C:\Program Files\MetaTrader 5\terminal64.exe"),
        terminal_data_root=Path(r"C:\Users\Ivan SQX\AppData\Roaming\MetaQuotes\Terminal\demo"),
        runtime_root=tmp_path,
    )

    assert values["CONNECTOR_BUFFER_DB_PATH"] == str(
        tmp_path / "runtime" / "g12" / "connector-buffer.sqlite"
    )


def test_g12_connector_profile_rejects_multiple_ingest_keys() -> None:
    with pytest.raises(ValueError, match="exactamente una"):
        build_values(
            {"INGEST_API_KEYS": "first,second"},
            account_login="demo-123",
            terminal_exe=Path("terminal64.exe"),
            terminal_data_root=Path("terminal"),
        )
