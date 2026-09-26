import json
from pathlib import Path

import pytest

from magic_identity import (
    IdentityValidationError,
    build_comment_identity,
    build_legacy_magic_map,
    entry_matches_account,
    load_policy,
    next_free_magic,
    normalize_short_label,
    parse_comment_identity,
    sha256_payload,
    strategy_key,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "magic_identity_policy.yaml"


def test_comment_round_trip_and_magic_suffix() -> None:
    policy = load_policy(POLICY_PATH)
    comment = build_comment_identity("DAXM30stat_2.13.18", 42, policy)

    assert comment == "DAXM30stat_2.13.18_MN42"
    assert parse_comment_identity(comment, policy) == ("DAXM30stat_2.13.18", 42)


@pytest.mark.parametrize("value", ["label_MN0", "label_MN-1", "label_MNabc", "label_MN2147483648"])
def test_comment_rejects_reserved_or_invalid_magic(value: str) -> None:
    with pytest.raises(IdentityValidationError):
        parse_comment_identity(value, load_policy(POLICY_PATH))


def test_long_label_requires_review_instead_of_silent_truncation() -> None:
    policy = load_policy(POLICY_PATH)
    label = normalize_short_label("Estrategia muy larga con caracteres áéíóú", policy)

    assert label.startswith("Estrategiamuylarga")
    with pytest.raises(IdentityValidationError, match="excede"):
        build_comment_identity(label, 42, policy)


def test_strategy_key_uses_technical_evidence_not_name() -> None:
    policy = load_policy(POLICY_PATH)
    evidence = {"ea_sha256": "a" * 64, "symbol": "EURUSD", "timeframe": "H1"}

    assert strategy_key(evidence, policy) == strategy_key(evidence, policy)
    assert strategy_key(evidence, policy).startswith("sk_v1_")
    with pytest.raises(IdentityValidationError, match="evidencia obligatoria"):
        strategy_key({"ea_sha256": "a" * 64, "symbol": "EURUSD"}, policy)


def test_next_free_magic_never_reuses_reserved_or_retired() -> None:
    assert next_free_magic({1, 2, 4}, load_policy(POLICY_PATH)) == 3


def test_payload_hash_is_deterministic() -> None:
    assert sha256_payload({"b": 1, "a": [2]}) == sha256_payload({"a": [2], "b": 1})


# --- Mapa de magics legacy -> identidad vigente (P2.2) ---------------------------------

def _registro(tmp_path, eventos):
    ruta = tmp_path / "registry.jsonl"
    ruta.write_text(
        "\n".join(json.dumps(evento, ensure_ascii=False) for evento in eventos) + "\n",
        encoding="utf-8",
    )
    return ruta


def _asignacion(comment, magic, legacy, accounts=("BEPB",)):
    return {
        "event_type": "ASSIGNED",
        "comment_identity": comment,
        "magic_number": magic,
        "legacy_magic_numbers": list(legacy),
        "accounts": list(accounts),
        "proposal_payload_sha256": "prop",
    }


def test_legacy_map_translates_an_assigned_magic(tmp_path) -> None:
    ruta = _registro(tmp_path, [_asignacion("XAUH1BUYSTOPeof_1.8.81_MN1", 1, [7786])])

    mapa = build_legacy_magic_map(ruta)

    assert mapa[7786]["magic_number"] == 1
    assert mapa[7786]["comment_identity"] == "XAUH1BUYSTOPeof_1.8.81_MN1"


def test_legacy_map_ignores_events_that_are_not_assignments(tmp_path) -> None:
    ruta = _registro(
        tmp_path,
        [
            {"event_type": "MIGRATION_PLANNED", "magic_number": 9, "legacy_magic_numbers": [111]},
            _asignacion("A_MN1", 1, [7786]),
        ],
    )

    mapa = build_legacy_magic_map(ruta)

    assert 111 not in mapa
    assert 7786 in mapa


def test_legacy_map_refuses_an_ambiguous_legacy(tmp_path) -> None:
    """Un magic viejo que apuntase a dos identidades vigentes no traduce: una atribución
    ambigua es peor que ninguna."""
    ruta = _registro(
        tmp_path,
        [_asignacion("A_MN1", 1, [5000]), _asignacion("B_MN2", 2, [5000])],
    )

    mapa = build_legacy_magic_map(ruta)

    assert 5000 not in mapa


def test_legacy_map_skips_a_magic_that_did_not_change(tmp_path) -> None:
    ruta = _registro(tmp_path, [_asignacion("A_MN7507", 7507, [7507])])

    mapa = build_legacy_magic_map(ruta)

    assert mapa == {}


def test_entry_matches_account_solo_para_la_cuenta_declarada() -> None:
    """Incidente A16 (2026-09-26): un magic 1:1 en el mapa global aplicaba
    en las DOS cuentas reales aunque su evento solo declarase una. Este es
    el filtro que todo consumidor por-cuenta debe aplicar."""
    entrada = {"magic_number": 10, "accounts": ["JJTI"]}

    assert entry_matches_account(entrada, "JJTI-Real-Darwinex") is True
    assert entry_matches_account(entrada, "BEPB-Real-Darwinex") is False


def test_entry_matches_account_sin_accounts_no_esta_restringida() -> None:
    entrada = {"magic_number": 10, "accounts": []}

    assert entry_matches_account(entrada, "cualquier-cuenta") is True
