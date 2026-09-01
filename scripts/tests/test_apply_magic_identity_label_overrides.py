import json
from pathlib import Path

from apply_magic_identity_label_overrides import apply_overrides
from plan_magic_identity_migration import build_proposal

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config" / "magic_identity_policy.yaml"


def test_label_override_rebuilds_comment_and_filename(tmp_path: Path) -> None:
    long_name = "This label is intentionally much too long for the MT5 limit"
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "account_login": "1",
                "account_label": "JJTI",
                "records": [
                    {
                        "strategy_name": long_name,
                        "comment_identity": "LongLegacyLabel_MN100",
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
    assert proposal["rows"][0]["status"] == "PROPOSED"

    revised = apply_overrides(
        proposal,
        POLICY,
        {
            proposal["rows"][0]["strategy_key"]: {
                "canonical_strategy_name": None,
                "short_strategy_label": "EURH1v1",
            }
        },
        None,
    )

    assert revised["rows"][0]["status"] == "PROPOSED"
    assert revised["rows"][0]["comment_identity"] == "EURH1v1_MN1"
    assert revised["rows"][0]["file_identity"] == "EURH1v1_MN1"


def test_account_variants_split_a_legacy_label_conflict(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    records = [
        (first, "1", "BEPB", "XAU shared", "XAUM30Lstat_1.19.27_MN100"),
        (second, "2", "JJTI", "XAU shared", "XAUM30L_1.19.27_MN100"),
    ]
    for path, login, account, name, comment in records:
        path.write_text(
            json.dumps(
                {
                    "account_login": login,
                    "account_label": account,
                    "records": [
                        {
                            "strategy_name": name,
                            "comment_identity": comment,
                            "magic_number": 100,
                            "symbol": "XAUUSD",
                            "timeframe": "M30",
                            "ea_sha256": "b" * 64,
                            "status": "MATCHED_UNIQUE_VERSION",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    proposal = build_proposal([first, second], POLICY, None)
    original = proposal["rows"][0]
    assert original["status"] == "WITHHELD_LEGACY_LABEL_CONFLICT"

    revised = apply_overrides(
        proposal,
        POLICY,
        {
            original["strategy_key"]: {
                "canonical_strategy_name": None,
                "short_strategy_label": None,
                "deployment_variants": [
                    {"account_label": "BEPB", "short_strategy_label": "XAUM30L_1.19.27a"},
                    {"account_label": "JJTI", "short_strategy_label": "XAUM30L_1.19.27b"},
                ],
            }
        },
        None,
    )

    assert {row["accounts"][0] for row in revised["rows"]} == {"BEPB", "JJTI"}
    assert {row["short_strategy_label"] for row in revised["rows"]} == {
        "XAUM30L_1.19.27a",
        "XAUM30L_1.19.27b",
    }
    assert all(row["technical_strategy_key"] == original["strategy_key"] for row in revised["rows"])
