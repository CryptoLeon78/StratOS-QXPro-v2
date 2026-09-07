from __future__ import annotations

from dataclasses import dataclass

import pytest

from connector.verify_live_account import verify_account_identity


@dataclass
class FakeAccount:
    login: int


class FakeMt5:
    def __init__(self, *, initialized: bool = True, account: FakeAccount | None = None) -> None:
        self.initialized = initialized
        self.account = account
        self.shutdown_called = False

    def initialize(self, path: str) -> bool:
        return self.initialized

    def account_info(self) -> FakeAccount | None:
        return self.account

    def last_error(self) -> tuple[int, str]:
        return (0, "fake error")

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_verify_account_identity_accepts_the_expected_active_login() -> None:
    mt5 = FakeMt5(account=FakeAccount(login=4000059903))

    verify_account_identity(mt5, r"C:\\terminal64.exe", "4000059903")

    assert mt5.shutdown_called is True


def test_verify_account_identity_rejects_another_mt5_instance() -> None:
    mt5 = FakeMt5(account=FakeAccount(login=4000055216))

    with pytest.raises(RuntimeError, match="does not match"):
        verify_account_identity(mt5, r"C:\\terminal64.exe", "4000059903")

    assert mt5.shutdown_called is True


def test_verify_account_identity_rejects_missing_account_details() -> None:
    mt5 = FakeMt5(account=None)

    with pytest.raises(RuntimeError, match="returned no account"):
        verify_account_identity(mt5, r"C:\\terminal64.exe", "4000059903")

    assert mt5.shutdown_called is True


def test_verify_account_identity_rejects_failed_initialization() -> None:
    mt5 = FakeMt5(initialized=False)

    with pytest.raises(RuntimeError, match="initialize"):
        verify_account_identity(mt5, r"C:\\terminal64.exe", "4000059903")

    assert mt5.shutdown_called is False
