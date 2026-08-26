"""PARTE 5.2: DecisionLog append-only con hash-chain. Algoritmo no dado por
la spec (ver ASSUMPTIONS G3-02): SHA-256 de prev_hash + JSON canonico."""

from datetime import UTC, datetime

from core.db.enums import ActorType
from core.state_machines.hash_chain import GENESIS_HASH, compute_decision_hash

TS = datetime(2026, 8, 26, tzinfo=UTC)


def test_deterministic_same_inputs_same_hash() -> None:
    a = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"from": "VERDE", "to": "AMARILLO"},
    )
    b = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"from": "VERDE", "to": "AMARILLO"},
    )
    assert a == b
    assert len(a) == 64


def test_payload_key_order_does_not_change_hash() -> None:
    a = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"from": "VERDE", "to": "AMARILLO"},
    )
    b = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"to": "AMARILLO", "from": "VERDE"},
    )
    assert a == b


def test_different_payload_gives_different_hash() -> None:
    a = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"from": "VERDE", "to": "AMARILLO"},
    )
    b = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"from": "AMARILLO", "to": "NARANJA"},
    )
    assert a != b


def test_chain_integrity_second_entry_depends_on_first() -> None:
    first_hash = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"bot_id": 7},
    )
    second_hash = compute_decision_hash(
        prev_hash=first_hash,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"bot_id": 7},
    )
    # mismo payload/ts/actor/module, distinto prev_hash -> distinto hash
    tampered_second_hash = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.SYSTEM,
        module="semaphore",
        decision_type="SEMAPHORE_TRANSITION",
        payload={"bot_id": 7},
    )
    assert second_hash != tampered_second_hash
    assert tampered_second_hash == first_hash  # confirma que solo prev_hash cambio el resultado


def test_empty_payload_does_not_crash() -> None:
    h = compute_decision_hash(
        prev_hash=GENESIS_HASH,
        ts=TS,
        actor=ActorType.HUMAN,
        module="killswitch",
        decision_type="KILLSWITCH_CONFIRM",
        payload={},
    )
    assert len(h) == 64
