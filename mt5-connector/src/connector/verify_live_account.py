"""Verify read-only that an active MT5 path belongs to the expected account."""

from __future__ import annotations

import argparse
import sys
from typing import Protocol, cast


class AccountInfoProtocol(Protocol):
    login: int


class Mt5IdentityProtocol(Protocol):
    def initialize(self, path: str) -> bool: ...

    def account_info(self) -> AccountInfoProtocol | None: ...

    def last_error(self) -> tuple[int, str]: ...

    def shutdown(self) -> None: ...


def verify_account_identity(
    mt5: Mt5IdentityProtocol, terminal_path: str, expected_login: str
) -> None:
    """Raise when the active terminal cannot be identified as the expected account."""
    if not mt5.initialize(terminal_path):
        code, description = mt5.last_error()
        raise RuntimeError(f"MetaTrader5.initialize() failed: {code} {description}")
    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError("MetaTrader5.account_info() returned no account")
        if str(account.login) != expected_login:
            raise RuntimeError("Active MT5 account does not match the requested service account")
    finally:
        mt5.shutdown()


def _load_mt5() -> Mt5IdentityProtocol:
    import MetaTrader5 as mt5

    return cast(Mt5IdentityProtocol, mt5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal-path", required=True)
    parser.add_argument("--expected-login", required=True)
    args = parser.parse_args()
    verify_account_identity(_load_mt5(), args.terminal_path, args.expected_login)
    print("MT5 account identity verified.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
