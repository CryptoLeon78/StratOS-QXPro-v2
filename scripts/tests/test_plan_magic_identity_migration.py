import json
from pathlib import Path

from plan_magic_identity_migration import build_proposal, write_outputs
from validate_magic_identity import validate_proposal

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config" / "magic_identity_policy.yaml"


def _manifest(
    login: str,
    label: str,
    name: str,
    magic: int,
    digest: str,
    comment_label: str | None = None,
) -> dict[str, object]:
    return {
        "account_login": login,
        "account_label": label,
        "records": [
            {
                "strategy_name": name,
                "comment_identity": f"{comment_label or name.replace(' ', '')}_MN{magic}",
                "magic_number": magic,
                "symbol": "EURUSD",
                "timeframe": "H1",
                "ea_sha256": digest,
                "status": "MATCHED_UNIQUE_VERSION",
            }
        ],
    }


def test_proposal_groups_same_verified_strategy_across_accounts(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        json.dumps(_manifest("1", "JJTI", "EURUSD H1 v1", 100, "a" * 64)), encoding="utf-8"
    )
    second.write_text(
        json.dumps(_manifest("2", "BEPB", "EURUSD H1 v1", 200, "a" * 64)), encoding="utf-8"
    )

    proposal = build_proposal([first, second], POLICY, None)

    assert proposal["summary"]["eligible_deployments"] == 2
    assert proposal["summary"]["strategies"] == 1
    row = proposal["rows"][0]
    assert row["status"] == "PROPOSED"
    assert row["magic_number"] == 1
    assert row["comment_identity"] == "EURUSDH1v1_MN1"
    assert row["file_identity"] == row["comment_identity"]
    assert row["accounts"] == ["BEPB", "JJTI"]
    assert validate_proposal(proposal, POLICY) == {"PROPOSED": 1}
    json_path, csv_path = write_outputs(proposal, tmp_path / "output")
    assert json_path.is_file()
    assert csv_path.is_file()


def test_proposal_with_conflicting_canonical_names_is_withheld(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        json.dumps(_manifest("1", "JJTI", "First", 100, "a" * 64, "Shared")), encoding="utf-8"
    )
    second.write_text(
        json.dumps(_manifest("2", "BEPB", "Second", 200, "a" * 64, "Shared")), encoding="utf-8"
    )

    proposal = build_proposal([first, second], POLICY, None)

    assert proposal["rows"][0]["status"] == "WITHHELD_CANONICAL_NAME_CONFLICT"
    assert validate_proposal(proposal, POLICY) == {"WITHHELD_CANONICAL_NAME_CONFLICT": 1}


def test_duplicate_short_labels_require_explicit_approval(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        json.dumps(_manifest("1", "JJTI", "Same Label", 100, "a" * 64)), encoding="utf-8"
    )
    second.write_text(
        json.dumps(_manifest("2", "BEPB", "Same Label", 200, "b" * 64)), encoding="utf-8"
    )

    proposal = build_proposal([first, second], POLICY, None)

    assert {row["status"] for row in proposal["rows"]} == {"REQUIRES_LABEL_APPROVAL"}
    assert validate_proposal(proposal, POLICY) == {"REQUIRES_LABEL_APPROVAL": 2}
