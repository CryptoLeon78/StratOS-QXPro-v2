"""Funciones puras para la identidad compacta G13 de EAs MT5.

El módulo no abre terminales, no contacta cuentas y no escribe registros. Los
comandos de propuesta, registro y contraste lo usan para mantener la misma
gramática y las mismas comprobaciones fail-closed.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class IdentityValidationError(ValueError):
    """La evidencia no permite crear o validar una identidad de forma segura."""


@dataclass(frozen=True)
class MagicIdentityPolicy:
    policy_version: str
    separator: str
    max_chars: int
    label_pattern: str
    minimum_magic: int
    maximum_magic: int
    reserved_magics: frozenset[int]
    strategy_key_required_evidence: tuple[str, ...]


def canonical_json(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256_payload(payload: object) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def payload_without_hash(
    payload: Mapping[str, Any], field: str = "payload_sha256"
) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != field}


def load_policy(path: Path) -> MagicIdentityPolicy:
    """Carga JSON válido como YAML para no añadir un parser de despliegue nuevo."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        comment = raw["comment"]
        magic = raw["magic"]
        strategy_key = raw["strategy_key"]
        policy = MagicIdentityPolicy(
            policy_version=str(raw["policy_version"]),
            separator=str(comment["separator"]),
            max_chars=int(comment["max_chars"]),
            label_pattern=str(comment["label_pattern"]),
            minimum_magic=int(magic["minimum"]),
            maximum_magic=int(magic["maximum"]),
            reserved_magics=frozenset(int(value) for value in magic["reserved"]),
            strategy_key_required_evidence=tuple(
                str(value) for value in strategy_key["required_evidence"]
            ),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise IdentityValidationError(f"política G13 inválida: {path.name}") from error
    if (
        policy.max_chars < 1
        or policy.minimum_magic < 1
        or policy.minimum_magic > policy.maximum_magic
    ):
        raise IdentityValidationError("rango o longitud de política G13 inválidos")
    if not policy.separator or re.search(r"\s", policy.separator):
        raise IdentityValidationError("separador de comment inválido")
    return policy


def normalize_short_label(canonical_name: str, policy: MagicIdentityPolicy) -> str:
    """Normaliza sin truncar; una abreviatura requiere aprobación humana posterior."""
    normalized = (
        unicodedata.normalize("NFKD", canonical_name).encode("ascii", "ignore").decode("ascii")
    )
    label = re.sub(r"\s+", "", normalized)
    label = re.sub(rf"[^{policy.label_pattern[1:-2]}]", "", label)
    label = label.strip("._-")
    if not label or re.fullmatch(policy.label_pattern, label) is None:
        raise IdentityValidationError("nombre canónico sin etiqueta MT5 válida")
    return label


def build_comment_identity(label: str, magic_number: int, policy: MagicIdentityPolicy) -> str:
    if re.fullmatch(policy.label_pattern, label) is None:
        raise IdentityValidationError("short_strategy_label inválido")
    validate_magic_number(magic_number, policy)
    comment = f"{label}{policy.separator}{magic_number}"
    if len(comment) > policy.max_chars:
        raise IdentityValidationError("comment excede el máximo de la política")
    return comment


def parse_comment_identity(comment: str, policy: MagicIdentityPolicy) -> tuple[str, int]:
    match = re.fullmatch(rf"({policy.label_pattern}){re.escape(policy.separator)}([0-9]+)", comment)
    if match is None:
        raise IdentityValidationError("comment_identity no cumple la gramática G13")
    magic_number = int(match.group(2))
    validate_magic_number(magic_number, policy)
    if len(comment) > policy.max_chars:
        raise IdentityValidationError("comment_identity excede el máximo de la política")
    return match.group(1), magic_number


def validate_magic_number(magic_number: int, policy: MagicIdentityPolicy) -> None:
    if isinstance(magic_number, bool) or not isinstance(magic_number, int):
        raise IdentityValidationError("magic_number debe ser un entero")
    if magic_number in policy.reserved_magics:
        raise IdentityValidationError("magic_number reservado")
    if not policy.minimum_magic <= magic_number <= policy.maximum_magic:
        raise IdentityValidationError("magic_number fuera del rango permitido")


def strategy_key(evidence: Mapping[str, Any], policy: MagicIdentityPolicy) -> str:
    """Deriva la clave de evidencia técnica, nunca de nombres, rutas o cuentas."""
    material: dict[str, str] = {}
    for key in policy.strategy_key_required_evidence:
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            raise IdentityValidationError(f"evidencia obligatoria ausente: {key}")
        material[key] = value.strip().casefold()
    digest = sha256_payload({"algorithm": "sha256-json-v1", "evidence": material})
    return f"sk_v1_{digest}"


def next_free_magic(used_magics: Iterable[int], policy: MagicIdentityPolicy) -> int:
    used = set(used_magics) | set(policy.reserved_magics)
    candidate = policy.minimum_magic
    while candidate in used and candidate <= policy.maximum_magic:
        candidate += 1
    if candidate > policy.maximum_magic:
        raise IdentityValidationError("no quedan magics disponibles en el rango configurado")
    return candidate


def verify_payload_hash(payload: Mapping[str, Any], field: str = "payload_sha256") -> None:
    expected = payload.get(field)
    if not isinstance(expected, str) or expected != sha256_payload(
        payload_without_hash(payload, field)
    ):
        raise IdentityValidationError("payload_sha256 inválido")


def build_legacy_magic_map(registry_path: Path) -> dict[int, dict[str, Any]]:
    """Mapa `magic anterior a la migración` -> identidad vigente.

    La migración de identidad compacta (G13-18/G13-20) cambió el magic de los EAs
    desplegados. Los deals anteriores al cambio llevan el magic **viejo**, así que una
    atribución por magic actual los deja huérfanos: en el export real de JJTI/BEPB hay 203
    y 128 magics distintos frente a 32 y 24 EAs registrados.

    El registro append-only conserva `legacy_magic_numbers` en cada evento `ASSIGNED`, que
    es la única fuente admisible para esta traducción: no se deduce de nombres ni de
    comentarios. Si dos identidades declarasen el mismo legacy, se retienen las dos y ese
    magic no traduce -- una atribución ambigua es peor que ninguna.
    """
    asignaciones: dict[int, list[dict[str, Any]]] = {}
    with registry_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if event.get("event_type") != "ASSIGNED":
                continue
            for legacy in event.get("legacy_magic_numbers") or []:
                asignaciones.setdefault(int(legacy), []).append(event)

    mapa: dict[int, dict[str, Any]] = {}
    for legacy, eventos in asignaciones.items():
        magics = {int(event["magic_number"]) for event in eventos}
        if len(magics) != 1:
            continue  # ambiguo: el magic viejo apuntaría a dos identidades vigentes
        event = eventos[0]
        if legacy == int(event["magic_number"]):
            continue  # no cambió: no hay nada que traducir
        mapa[legacy] = {
            "magic_number": int(event["magic_number"]),
            "comment_identity": event.get("comment_identity"),
            "accounts": event.get("accounts") or [],
            "proposal_payload_sha256": event.get("proposal_payload_sha256"),
        }
    return mapa


def entry_matches_account(entry: Mapping[str, Any], account_name: str) -> bool:
    """¿Esta entrada de `build_legacy_magic_map()` aplica a `account_name`?

    Cada evento `ASSIGNED` declara a qué cuenta pertenece (`accounts`, p.ej.
    `["JJTI"]`); dos cuentas reales pueden reutilizar el mismo magic legacy
    con destinos distintos, así que un consumidor que ignore este campo
    aplica traducciones de una cuenta a la otra (incidente A16,
    2026-09-26: `Trade.magic_number` de BEPB y JJTI escrito con el valor de
    la cuenta contraria). Toda función que traduzca magics de UNA cuenta
    concreta debe filtrar `legacy_magic_map` con esto antes de usarlo --
    nunca aplicar el mapa global tal cual.

    Sin `accounts` declarado, la traducción no está restringida (mismo
    criterio que ya usaba `sync_bot_magics_to_migration.py`).
    """
    etiquetas = [str(label) for label in entry.get("accounts") or []]
    if not etiquetas:
        return True
    return any(etiqueta.upper() in account_name.upper() for etiqueta in etiquetas)
