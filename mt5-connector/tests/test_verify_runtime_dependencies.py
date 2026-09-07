from __future__ import annotations

from types import ModuleType

import pytest

from connector.verify_runtime_dependencies import verify_runtime_dependencies


def test_verify_runtime_dependencies_imports_the_required_modules() -> None:
    imported: list[str] = []

    def load_module(name: str) -> ModuleType:
        imported.append(name)
        return ModuleType(name)

    verify_runtime_dependencies(load_module)

    assert imported == ["MetaTrader5", "connector", "ingest_seal"]


def test_verify_runtime_dependencies_preserves_import_failure() -> None:
    def load_module(name: str) -> ModuleType:
        if name == "MetaTrader5":
            raise ModuleNotFoundError(name)
        return ModuleType(name)

    with pytest.raises(ModuleNotFoundError):
        verify_runtime_dependencies(load_module)
