"""Reglas puras de la proyección F1 tras eventos del agente."""

import pytest

from core.routers.pipeline_orchestrator import _work_item_status


@pytest.mark.parametrize(
    ("command_type", "expected"),
    [
        ("FORJA_GENERATE", "GENERATED"),
        ("SQX_START", "MINING"),
        ("SQX_STOP", "STOPPED"),
    ],
)
def test_f1_successful_agent_event_updates_the_visible_status(
    command_type: str, expected: str
) -> None:
    assert _work_item_status(command_type, "SUCCEEDED") == expected


@pytest.mark.parametrize("command_type", ["FORJA_GENERATE", "SQX_START", "SQX_STOP"])
def test_f1_failed_agent_event_is_never_promoted(command_type: str) -> None:
    assert _work_item_status(command_type, "FAILED") == "FAILED"
