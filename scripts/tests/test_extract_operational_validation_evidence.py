import base64
import struct
import xml.etree.ElementTree as etree
import zipfile
from pathlib import Path

from extract_operational_validation_evidence import (
    preferred_artifact,
    sqstats_net_profit,
    wfm_project_criteria,
)


def _sqstats(records: bytes, version: int = 2) -> etree.Element:
    element = etree.Element("SQStats", {"version": str(version), "e": "b64"})
    element.text = base64.b64encode(records).decode("ascii")
    return element


def test_sqstats_net_profit_reads_sqx144_compact_float() -> None:
    payload = b"\x03\x0a" + struct.pack(">f", 1234.5) + b"\x01\x00" + struct.pack(">i", 7)

    assert sqstats_net_profit(_sqstats(payload)) == 1234.5


def test_sqstats_net_profit_rejects_unknown_record_type() -> None:
    try:
        sqstats_net_profit(_sqstats(b"\xff"))
    except ValueError as exc:
        assert "desconocido" in str(exc)
    else:
        raise AssertionError("se esperaba retención del formato SQStats desconocido")


def test_forward_uses_resolved_source_match_before_databank_variants() -> None:
    item = {
        "strategy_identifier": "1.2.3",
        "source_matches": [
            {"databank_bucket": "Forward", "path": "direct.sqx", "sha256": "a"},
        ],
        "validation_artifacts": [
            {"databank_bucket": "Forward", "path": "first.sqx", "sha256": "b"},
            {"databank_bucket": "Forward", "path": "second.sqx", "sha256": "c"},
        ],
    }

    assert preferred_artifact(item, "Forward")["path"] == "direct.sqx"


def test_wfm_uses_full_strategy_suffix_when_identifier_is_normalized() -> None:
    item = {
        "strategy_name": "AUDCADH4S_Strategy 3.6.50(1)_wfm520",
        "strategy_identifier": "3.6.50",
        "validation_artifacts": [
            {"databank_bucket": "WFM", "path": "Strategy 3.6.50(1).sqx", "sha256": "a"},
            {"databank_bucket": "WFM", "path": "Strategy 3.6.50(1)_wfm520.sqx", "sha256": "b"},
        ],
    }

    assert preferred_artifact(item, "WFM")["path"] == "Strategy 3.6.50(1)_wfm520.sqx"


def test_wfm_project_criteria_reads_the_active_retest_task(tmp_path: Path) -> None:
    project = tmp_path / "project.cfx"
    config = """<Project><Tasks><Task type=\"Retest\" name=\"WFM\" title=\"Walk forward\" taskXMLFile=\"Retest-Task6.xml\" /></Tasks></Project>"""
    task = """<Task><WalkForwardMatrix use=\"true\"><Settings><WalkForward period=\"10\" optimization=\"25\"><Param1 start=\"10\" stop=\"35\" step=\"5\" /></WalkForward></Settings><AcceptanceSettings><Conditions CrossCheck=\"WalkForwardMatrix\" thresholdPct=\"80\" robustCombinationRows=\"3\"><Condition use=\"true\"><Left-Side><Column-Value column=\"NetProfit\" /></Left-Side><Comparator>&gt;</Comparator><Right-Side><Numeric-Value value=\"0\" /></Right-Side></Condition></Conditions></AcceptanceSettings></WalkForwardMatrix></Task>"""
    with zipfile.ZipFile(project, "w") as archive:
        archive.writestr("config.xml", config)
        archive.writestr("Retest-Task6.xml", task)

    import hashlib

    result = wfm_project_criteria(
        {"path": str(project), "sha256": hashlib.sha256(project.read_bytes()).hexdigest()}
    )

    assert result["criteria"]["task"]["xml"] == "Retest-Task6.xml"
    assert result["criteria"]["walk_forward"]["period"] == "10"
    assert result["criteria"]["acceptance"]["thresholdPct"] == "80"
