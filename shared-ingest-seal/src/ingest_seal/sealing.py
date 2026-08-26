"""PARTE 6/9.1: sellado SHA-256 de un lote de ingesta. El conector calcula
esto ANTES de tocar la red (lo que se guarda en el buffer SQLite ya va
sellado); el servidor recalcula sobre el payload recibido y compara -- ver
ASSUMPTIONS.md G4 para el diseno completo de la mecanica de sellado."""

import hashlib
import json
from typing import Any


class SealMismatchError(Exception):
    """El SHA-256 declarado por el cliente no coincide con el recalculado
    sobre el payload recibido -- indicio de corrupcion o manipulacion."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"seal mismatch: expected={expected} actual={actual}")


def canonical_batch_json(account_login: str, batch_type: str, records: list[dict[str, Any]]) -> str:
    """Mismo criterio de canonicalizacion que hash_chain.compute_decision_hash
    (G3): claves ordenadas, sin espacios, default=str para tipos no nativos
    de JSON (Decimal, datetime) que puedan colarse en un record ya volcado
    a dict."""
    return json.dumps(
        {"account_login": account_login, "batch_type": batch_type, "records": records},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def compute_batch_sha256(account_login: str, batch_type: str, records: list[dict[str, Any]]) -> str:
    canonical = canonical_batch_json(account_login, batch_type, records)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_batch_seal(
    claimed_sha256: str, account_login: str, batch_type: str, records: list[dict[str, Any]]
) -> None:
    actual = compute_batch_sha256(account_login, batch_type, records)
    if actual != claimed_sha256:
        raise SealMismatchError(claimed_sha256, actual)
