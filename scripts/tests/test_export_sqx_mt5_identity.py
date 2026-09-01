import json
from pathlib import Path

import pytest

from export_sqx_mt5_identity import validate_delivery
from magic_identity import IdentityValidationError
from plan_magic_identity_migration import build_proposal
from record_magic_identity_registry import prepare_events

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config" / "magic_identity_policy.yaml"


def test_delivery_requires_exact_registered_magic_and_comment(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "account_login": "1",
                "account_label": "JJTI",
                "records": [
                    {
                        "strategy_name": "EURUSD H1 v1",
                        "comment_identity": "EURUSDH1v1_MN100",
                        "magic_number": 100,
                        "symbol": "EURUSD",
                        "timeframe": "H1",
                        "ea_sha256": "a" * 64,
                        "status": "MATCHED_UNIQUE_VERSION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proposal = build_proposal([source], POLICY, None)
    assignment = prepare_events(proposal, [], "operator-review-1", None)[0]
    delivery = {
        "strategy_key": assignment["strategy_key"],
        "magic_number": assignment["magic_number"],
        "custom_comment": assignment["comment_identity"],
        "ea_sha256": "a" * 64,
        "symbol": "EURUSD",
        "timeframe": "H1",
    }

    assert (
        validate_delivery(delivery, {assignment["strategy_key"]: assignment}, POLICY) == assignment
    )
    delivery["custom_comment"] = "wrong#1"
    with pytest.raises(IdentityValidationError, match="CustomComment"):
        validate_delivery(delivery, {assignment["strategy_key"]: assignment}, POLICY)
