from __future__ import annotations

import pytest

from scripts.create_g12_operator import _assert_g12_database


def test_create_g12_operator_rejects_any_non_g12_database() -> None:
    with pytest.raises(ValueError, match="stratos_g12"):
        _assert_g12_database("postgresql+asyncpg://user:password@localhost:55432/stratos")


def test_create_g12_operator_accepts_isolated_g12_database() -> None:
    _assert_g12_database("postgresql+asyncpg://user:password@localhost:56432/stratos_g12")
