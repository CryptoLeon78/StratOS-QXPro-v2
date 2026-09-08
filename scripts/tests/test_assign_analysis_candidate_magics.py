import json
from pathlib import Path

from assign_analysis_candidate_magics import apply_assignment, plan_assignment
from assign_unique_magics import read_magic


def _policy(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "policy_version": "test",
                "comment": {
                    "separator": "_MN",
                    "max_chars": 30,
                    "label_pattern": "[A-Za-z0-9_.-]+",
                },
                "magic": {"minimum": 1, "maximum": 2147483647, "reserved": [0]},
                "strategy_key": {"required_evidence": ["ea_sha256", "symbol", "timeframe"]},
                "allocation_scopes": {
                    "analysis_candidate": {"minimum": 1000000, "maximum": 1000002}
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _ea(path: Path, magic: int) -> None:
    path.write_text(f"input int MagicNumber = {magic}; // Magic number\n", encoding="utf-8")


def test_assigns_every_candidate_in_a_dedicated_scope(tmp_path: Path) -> None:
    first = tmp_path / "a.mq5"
    second = tmp_path / "b.mq5"
    _ea(first, 11111)
    _ea(second, 11111)
    rows = plan_assignment([tmp_path], _policy(tmp_path / "policy.json"), "analysis_candidate")

    assert [row["magic_number_after"] for row in rows] == [1000000, 1000001]
    apply_assignment(rows)
    assert [read_magic(first), read_magic(second)] == [1000000, 1000001]
    assert all("mql5_sha256_after" in row for row in rows)


def test_refuses_a_source_without_magic(tmp_path: Path) -> None:
    (tmp_path / "missing.mq5").write_text("input double Lots = 0.1;", encoding="utf-8")

    try:
        plan_assignment([tmp_path], _policy(tmp_path / "policy.json"), "analysis_candidate")
    except ValueError as error:
        assert "MagicNumber ausente" in str(error)
    else:
        raise AssertionError("expected MagicNumber validation failure")
