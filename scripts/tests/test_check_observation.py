"""Avoid false readiness when a real account never reported or stopped reporting."""

import pytest

from check_observation import telemetry_ready


@pytest.mark.parametrize(
    "accounts",
    [
        [],
        [{"heartbeat_age_seconds": None, "equity_age_seconds": None}],
        [{"heartbeat_age_seconds": 1, "equity_age_seconds": None}],
        [
            {"heartbeat_age_seconds": 1, "equity_age_seconds": 1},
            {"heartbeat_age_seconds": 121, "equity_age_seconds": 1},
        ],
        [{"heartbeat_age_seconds": -1, "equity_age_seconds": 1}],
    ],
)
def test_missing_stale_or_future_telemetry_blocks(accounts):
    assert not telemetry_ready(accounts, 120)


def test_all_real_accounts_need_both_streams_within_configured_window():
    accounts = [
        {"heartbeat_age_seconds": 30, "equity_age_seconds": 50},
        {"heartbeat_age_seconds": 60, "equity_age_seconds": 75},
    ]
    assert telemetry_ready(accounts, 75)
    assert not telemetry_ready(accounts, 74)
