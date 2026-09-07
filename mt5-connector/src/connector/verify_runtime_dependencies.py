"""Verify that the installed runtime can import every connector dependency."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from types import ModuleType

_REQUIRED_MODULES = ("MetaTrader5", "connector", "ingest_seal")


def verify_runtime_dependencies(
    load_module: Callable[[str], ModuleType] = import_module,
) -> None:
    """Import the deployed dependencies without connecting to a terminal."""
    for module_name in _REQUIRED_MODULES:
        load_module(module_name)


def main() -> None:
    verify_runtime_dependencies()
    print("Readonly connector dependencies ready")


if __name__ == "__main__":
    main()
