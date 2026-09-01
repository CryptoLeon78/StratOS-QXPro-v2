import json
from pathlib import Path

from plan_magic_identity_migration import build_proposal
from record_magic_identity_registry import _read_events, prepare_events

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config" / "magic_identity_policy.yaml"


def test_registry_events_are_append_only_and_chain_sealed(tmp_path: Path) -> None:
    manifest = tmp_path / "source.json"
    manifest.write_text(
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
    proposal = build_proposal([manifest], POLICY, None)
    events = prepare_events(proposal, [], "operator-review-1", None)

    assert [event["event_type"] for event in events] == ["ASSIGNED", "MIGRATION_PLANNED"]
    assert events[1]["prev_event_sha256"] == events[0]["payload_sha256"]
    registry = tmp_path / "registry.jsonl"
    registry.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    assert _read_events(registry) == events
