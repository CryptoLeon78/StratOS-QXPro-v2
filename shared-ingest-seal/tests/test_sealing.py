"""PARTE 6/9.1: canonicalizacion + SHA-256 de un lote de ingesta. Mismo
criterio que hash_chain.py (G3): claves ordenadas, sin espacios, default=str
para tipos no nativos de JSON (Decimal, datetime)."""

from decimal import Decimal

import pytest

from ingest_seal.sealing import (
    SealMismatchError,
    canonical_batch_json,
    compute_batch_sha256,
    verify_batch_seal,
)


def test_canonical_json_is_deterministic() -> None:
    a = canonical_batch_json("100231", "trades", [{"ticket": 1, "profit": "10.50"}])
    b = canonical_batch_json("100231", "trades", [{"ticket": 1, "profit": "10.50"}])
    assert a == b


def test_canonical_json_ignores_key_order_within_a_record() -> None:
    a = canonical_batch_json("100231", "trades", [{"ticket": 1, "profit": "10.50"}])
    b = canonical_batch_json("100231", "trades", [{"profit": "10.50", "ticket": 1}])
    assert a == b


def test_canonical_json_has_no_whitespace() -> None:
    result = canonical_batch_json("100231", "trades", [{"ticket": 1}])
    assert " " not in result


def test_canonical_json_handles_non_json_native_values_via_default_str() -> None:
    # Decimal no es serializable por json.dumps sin un `default=` -- no debe
    # lanzar (mismo criterio de robustez que hash_chain.compute_decision_hash).
    result = canonical_batch_json("100231", "equity", [{"equity": Decimal("179642.70")}])
    assert "179642.70" in result


def test_compute_batch_sha256_is_deterministic_hex64() -> None:
    a = compute_batch_sha256("100231", "trades", [{"ticket": 1}])
    b = compute_batch_sha256("100231", "trades", [{"ticket": 1}])
    assert a == b
    assert len(a) == 64
    assert all(c in "0123456789abcdef" for c in a)


def test_different_records_give_different_hash() -> None:
    a = compute_batch_sha256("100231", "trades", [{"ticket": 1}])
    b = compute_batch_sha256("100231", "trades", [{"ticket": 2}])
    assert a != b


def test_different_account_login_gives_different_hash() -> None:
    a = compute_batch_sha256("100231", "trades", [{"ticket": 1}])
    b = compute_batch_sha256("100232", "trades", [{"ticket": 1}])
    assert a != b


def test_different_batch_type_gives_different_hash() -> None:
    a = compute_batch_sha256("100231", "trades", [{"ticket": 1}])
    b = compute_batch_sha256("100231", "positions", [{"ticket": 1}])
    assert a != b


def test_empty_records_does_not_crash() -> None:
    result = compute_batch_sha256("100231", "heartbeat", [])
    assert len(result) == 64


def test_verify_batch_seal_passes_when_hash_matches() -> None:
    records = [{"ticket": 1}]
    seal = compute_batch_sha256("100231", "trades", records)
    verify_batch_seal(seal, "100231", "trades", records)  # no debe lanzar


def test_verify_batch_seal_raises_on_mismatch() -> None:
    records = [{"ticket": 1}]
    seal = compute_batch_sha256("100231", "trades", records)
    # un solo caracter distinto, garantizado != al original (no "f" a ciegas:
    # 1/16 de las veces el propio hash ya empezaria por "f")
    tampered = ("0" if seal[0] != "0" else "1") + seal[1:]
    with pytest.raises(SealMismatchError) as exc_info:
        verify_batch_seal(tampered, "100231", "trades", records)
    assert exc_info.value.expected == tampered
    assert exc_info.value.actual == seal
