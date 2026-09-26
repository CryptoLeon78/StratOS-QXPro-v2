import pytest

from scan_mt5_chart_identity import _logical_charts, _mt5_chart_id, _values, profile_chart_root


def test_uses_the_mt5_data_folder_profile_location() -> None:
    assert profile_chart_root("StratOS_Incubadora") == "Profiles/Charts/StratOS_Incubadora"


@pytest.mark.parametrize("profile", ["", "../Default", "Default/other"])
def test_rejects_non_profile_path(profile: str) -> None:
    with pytest.raises(ValueError, match="profile"):
        profile_chart_root(profile)


def test_keeps_ea_name_when_chart_contains_trade_object_names() -> None:
    payload = (
        "name=EURGBP_H1_LS_estadistico_Strategy 1.12.29\n"
        "CustomComment=EUGBH1LS_1.12.29a_MN2\n"
        "MagicNumber=2\n"
        "name=autotrade #1 -> #2, profit 1.00, EURGBP\n"
    ).encode("utf-16")

    assert _values(payload) == {
        "name": "EURGBP_H1_LS_estadistico_Strategy 1.12.29",
        "CustomComment": "EUGBH1LS_1.12.29a_MN2",
        "MagicNumber": "2",
    }


def test_collapses_equivalent_profile_serializations_by_mt5_chart_id() -> None:
    common = {
        "mt5_chart_id": "123",
        "ea_filename": "EURGBPH1L_5.12.175_MN30",
        "magic_number": 30,
        "comment_identity": "EURGBPH1L_5_12_175_MN30",
        "symbol": "EURGBP",
    }
    logical, duplicates, conflicts = _logical_charts(
        [
            {**common, "chart_relative_path": "Profiles/Charts/Default/chart17.chr"},
            {**common, "chart_relative_path": "Profiles/Charts/Default/chart19.chr"},
        ]
    )

    assert len(logical) == 1
    assert logical[0]["profile_serialization_paths"] == [
        "Profiles/Charts/Default/chart17.chr",
        "Profiles/Charts/Default/chart19.chr",
    ]
    assert duplicates[0]["mt5_chart_id"] == "123"
    assert conflicts == []


def test_reads_only_the_root_mt5_chart_id() -> None:
    payload = "<chart>\r\nid=123\r\n<object>\r\nid=456\r\n".encode("utf-16")

    assert _mt5_chart_id(payload) == "123"
