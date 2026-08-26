"""PARTE 5.2: DecisionLog append-only con hash-chain. Algoritmo (ASSUMPTIONS
G3-02): SHA-256 de prev_hash + JSON canonico del resto de campos."""

import hashlib
import json
from datetime import datetime
from typing import Any

from core.db.enums import ActorType

GENESIS_HASH = "0" * 64


def compute_decision_hash(
    prev_hash: str,
    ts: datetime,
    actor: ActorType,
    module: str,
    decision_type: str,
    payload: dict[str, Any],
) -> str:
    """SHA-256 de `prev_hash` + JSON canonico (claves ordenadas, sin
    espacios) del resto de campos -- mismo criterio de sellado que
    `IngestBatch.sha256` (G1), verificable sin depender de detalles de
    implementacion de Python."""
    canonical = json.dumps(
        {
            "ts": ts.isoformat(),
            "actor": actor.value,
            "module": module,
            "decision_type": decision_type,
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()
