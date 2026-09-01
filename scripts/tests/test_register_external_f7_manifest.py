import json

import pytest

from register_external_f7_manifest import _load_manifest


def test_load_manifest_keeps_only_closed_associations(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "account_login": "4000059903",
                "account_label": "JJTI",
                "records": [
                    {
                        "strategy_name": "closed",
                        "comment_identity": "closed|magic=1",
                        "magic_number": 1,
                        "symbol": "EURUSD",
                        "timeframe": "H1",
                        "ea_relative_path": "Experts/closed.ex5",
                        "ea_sha256": "a" * 64,
                        "status": "MATCHED_UNIQUE_VERSION",
                    },
                    {"magic_number": 2, "status": "WITHHELD_AMBIGUOUS_DEPLOYED_EX5"},
                ],
            }
        ),
        encoding="utf-8",
    )

    login, records, withheld = _load_manifest(path)

    assert login == "4000059903"
    assert [record.magic_number for record in records] == [1]
    assert withheld == 1


def test_load_manifest_rejects_incomplete_eligible_record(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "account_login": "4000059903",
                "account_label": "JJTI",
                "records": [{"magic_number": 1, "status": "MATCHED_UNIQUE_VERSION"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="fila elegible incompleta"):
        _load_manifest(path)
