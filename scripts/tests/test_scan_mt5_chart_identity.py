import pytest

import attach_g12_demo_eas
from scan_mt5_chart_identity import (
    TIMEFRAME_TO_PERIOD,
    _logical_charts,
    _mt5_chart_id,
    _timeframe,
    _values,
    profile_chart_root,
)


def _chr(period_type: int, period_size: int, extra: str = "") -> bytes:
    return (
        f"<chart>\r\nid=1\r\nsymbol=EURUSD\r\nperiod_type={period_type}\r\n"
        f"period_size={period_size}\r\n{extra}"
    ).encode("utf-16")


# Pares (period_type, period_size) observados en perfiles .chr reales de MT5 build 6182:
# (0,30)=M30, (1,1)=H1, (1,4)=H4, (1,24)=D1. MT5 no guarda una clave `period`.
@pytest.mark.parametrize(
    ("pair", "timeframe"),
    [((0, 30), "M30"), ((1, 1), "H1"), ((1, 4), "H4"), ((1, 24), "D1")],
)
def test_reads_timeframe_from_period_type_and_size(pair: tuple[int, int], timeframe: str) -> None:
    assert _timeframe(_chr(*pair)) == timeframe


def test_timeframe_is_none_when_the_profile_has_no_period_keys() -> None:
    assert _timeframe("<chart>\r\nid=1\r\nsymbol=EURUSD\r\n".encode("utf-16")) is None


def test_unknown_period_pair_stays_visible_instead_of_being_dropped() -> None:
    # Fail-closed: un par no mapeado debe llegar al consumidor como valor que no
    # coincide con ningun timeframe aprobado, nunca como None ni como otro TF.
    assert _timeframe(_chr(3, 7)) == "period_type=3,period_size=7"


def test_timeframe_uses_only_the_first_period_block() -> None:
    payload = _chr(1, 1, "<indicator>\r\nperiod_type=0\r\nperiod_size=5\r\n")

    assert _timeframe(payload) == "H1"


def test_attach_and_scan_agree_on_every_timeframe_encoding() -> None:
    # Escribir un perfil y volver a leerlo debe dar el mismo timeframe: una sola
    # verdad para los dos sentidos. Antes M1/M5/M15 se escribian como horas.
    assert attach_g12_demo_eas.TIMEFRAME_TO_PERIOD == TIMEFRAME_TO_PERIOD
    for timeframe, pair in TIMEFRAME_TO_PERIOD.items():
        assert _timeframe(_chr(*pair)) == timeframe
    assert len(set(TIMEFRAME_TO_PERIOD.values())) == len(TIMEFRAME_TO_PERIOD)


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
