from pathlib import Path

import pytest

from magic_identity import (
    IdentityValidationError,
    build_comment_identity,
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
