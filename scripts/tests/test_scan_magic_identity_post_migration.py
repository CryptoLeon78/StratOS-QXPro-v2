import json
from pathlib import Path

from plan_magic_identity_migration import build_proposal
from scan_magic_identity_post_migration import (
    _symbol_alias,
    compare_scan,
    load_scan_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config" / "magic_identity_policy.yaml"


def test_post_scan_requires_an_exact_identity_match(tmp_path: Path) -> None:
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
    row = proposal["rows"][0]
    scan = {
        "charts": [
            {
                "account_login": "1",
                "chart_id": "chart-a",
                "ea_filename": "EURUSDH1v1_MN1",
                "ea_sha256": "a" * 64,
                "magic_number": row["magic_number"],
                "comment_identity": row["comment_identity"],
                "symbol": "EURUSD",
                "timeframe": "H1",
            }
        ]
    }

    result = compare_scan(proposal, scan, POLICY)

    assert result["summary"] == {"MIGRATION_OBSERVED": 1}


def test_post_scan_preserves_dots_in_an_ea_identity_filename(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "account_login": "1",
                "account_label": "JJTI",
                "records": [
                    {
                        "strategy_name": "EURUSD H1 v1.2",
                        "comment_identity": "EURUSDH1v1.2_MN100",
                        "magic_number": 100,
                        "symbol": "EURUSD",
                        "timeframe": "H1",
                        "ea_sha256": "b" * 64,
                        "status": "MATCHED_UNIQUE_VERSION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proposal = build_proposal([source], POLICY, None)
    row = proposal["rows"][0]

    result = compare_scan(
        proposal,
        {
            "charts": [
                {
                    "account_login": "1",
                    "chart_id": "chart-a",
                    "ea_filename": f"{row['file_identity']}.ex5",
                    "ea_sha256": "b" * 64,
                    "magic_number": row["magic_number"],
                    "comment_identity": row["comment_identity"],
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                }
            ]
        },
        POLICY,
    )

    assert result["summary"] == {"MIGRATION_OBSERVED": 1}


def test_post_scan_accepts_the_persisted_mt5_comment_encoding(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "account_login": "1",
                "account_label": "JJTI",
                "records": [
                    {
                        "strategy_name": "EURUSD H1 v1.2",
                        "comment_identity": "EURUSDH1v1.2_MN100",
                        "magic_number": 100,
                        "symbol": "EURUSD",
                        "timeframe": "H1",
                        "ea_sha256": "c" * 64,
                        "status": "MATCHED_UNIQUE_VERSION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proposal = build_proposal([source], POLICY, None)
    row = proposal["rows"][0]

    result = compare_scan(
        proposal,
        {
            "profile_comment_encoding": "period_to_underscore",
            "charts": [
                {
                    "account_login": "1",
                    "chart_id": "chart-a",
                    "ea_filename": row["file_identity"],
                    "ea_sha256": "c" * 64,
                    "magic_number": row["magic_number"],
                    "comment_identity": row["comment_identity"].replace(".", "_"),
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                }
            ],
        },
        POLICY,
    )

    assert result["summary"] == {"MIGRATION_OBSERVED": 1}


def test_post_scan_preserves_f7_and_darwinex_dax_symbol_identities(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "account_login": "4000059903",
                "account_label": "JJTI",
                "records": [
                    {
                        "strategy_name": "DAX strategy 1.2",
                        "comment_identity": "DAXH1_1.2_MN100",
                        "magic_number": 100,
                        "symbol": "DAX",
                        "timeframe": "H1",
                        "ea_sha256": "d" * 64,
                        "status": "MATCHED_UNIQUE_VERSION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proposal = build_proposal([source], POLICY, None)
    row = proposal["rows"][0]

    result = compare_scan(
        proposal,
        {
            "charts": [
                {
                    "account_login": "4000059903",
                    "chart_id": "chart-a",
                    "ea_filename": row["file_identity"],
                    "ea_sha256": "d" * 64,
                    "magic_number": row["magic_number"],
                    "comment_identity": row["comment_identity"],
                    "symbol": "GDAXI",
                    "timeframe": "H1",
                }
            ]
        },
        POLICY,
    )

    observed = result["rows"][0]
    assert observed["status"] == "MIGRATION_OBSERVED"
    assert observed["symbol_identity"] == {
        "f7_source_symbol": "DAX",
        "mt5_broker_symbol": "GDAXI",
        "alias_id": "darwinex-dax-gdaxi-v1",
    }
    assert _symbol_alias(POLICY, "4000059903", "DAX40", "GDAXI") == {
        "alias_id": "darwinex-dax40-gdaxi-v1",
        "source_symbol": "DAX40",
        "broker_symbol": "GDAXI",
    }


def test_post_scan_marks_a_matching_operator_retained_exception(tmp_path: Path) -> None:
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
                        "ea_sha256": "e" * 64,
                        "status": "MATCHED_UNIQUE_VERSION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proposal = build_proposal([source], POLICY, None)
    retained = {
        ("1", 99): {
            "status": "OPERATOR_RETAINED_OUT_OF_PROPOSAL",
            "reason": "operator retained",
            "file_identity": "Retained_MN99",
            "configured_comment_identity": "Retained_MN99",
            "effective_comment_identity": "Retained_MN99",
            "ea_sha256": "f" * 64,
            "symbol_identity": {"mt5_broker_symbol": "EURUSD"},
            "timeframe": "H1",
            "manifest_payload_sha256": "a" * 64,
        }
    }

    result = compare_scan(
        proposal,
        {
            "charts": [
                {
                    "account_login": "1",
                    "chart_id": "chart-a",
                    "ea_filename": "Retained_MN99",
                    "ea_sha256": "f" * 64,
                    "magic_number": 99,
                    "comment_identity": "Retained_MN99",
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                }
            ]
        },
        POLICY,
        retained,
    )

    assert result["summary"]["OPERATOR_RETAINED_OUT_OF_PROPOSAL"] == 1


def test_post_scan_fails_closed_for_a_conflicting_mt5_chart_serialization(
    tmp_path: Path, monkeypatch
) -> None:
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
                        "ea_sha256": "g" * 64,
                        "status": "MATCHED_UNIQUE_VERSION",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proposal = build_proposal([source], POLICY, None)
    row = proposal["rows"][0]
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "account_login": "1",
                "charts": [
                    {
                        "chart_relative_path": "chart-a.chr",
                        "magic_number": row["magic_number"],
                        "comment_identity": row["comment_identity"],
                        "symbol": "EURUSD",
                        "period": "H1",
                    }
                ],
                "profile_chart_id_conflicts": [
                    {"chart_relative_paths": ["chart-a.chr", "chart-b.chr"]}
                ],
            }
        ),
        encoding="utf-8",
    )
    args = type(
        "Args",
        (),
        {
            "scan_manifest": None,
            "profile_scan_manifest": [profile],
            "visual_confirmation": None,
            "retained_exception_manifest": None,
            "identity_only_confirmed": True,
        },
    )()
    scan = load_scan_manifest(args, proposal)

    result = compare_scan(proposal, scan, POLICY)

    assert result["summary"] == {"MIGRATION_UNVERIFIED": 1}
    assert result["rows"][0]["reason"] == "PROFILE_CHART_ID_CONFLICT"
