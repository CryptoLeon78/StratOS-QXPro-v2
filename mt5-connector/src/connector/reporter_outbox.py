"""Lector read-only del outbox local que escriben los EAs gestionados."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from connector.buffer import Buffer
from connector.poller import _seal_and_serialize


def _decimal_json(value: object) -> str | None:
    if value is None:
        return None
    return str(Decimal(str(value)))


def canonicalize_reporter_event(batch_type: str, event: dict[str, object]) -> dict[str, object]:
    """Alinea los decimales del JSONL de MQL5 con el JSON canónico de Pydantic.

    Los EAs escriben números JSON y ``json.loads`` los vuelve ``float``. El
    core reconstruye esos campos como ``Decimal`` y los serializa como string
    antes de verificar el sello; sin esta conversión, un payload válido da 422
    por sello distinto. No se modifica el JSONL de origen.
    """
    # json.loads devuelve Any: la copia profunda se anota explicitamente para no
    # propagar ese Any al retorno declarado (mypy --strict, no-any-return).
    normalized: dict[str, object] = json.loads(json.dumps(event))
    if batch_type == "ea_state":
        eas = normalized.get("eas")
        if not isinstance(eas, list):
            raise ValueError("ea_state reporter sin lista eas")
        for ea in eas:
            if not isinstance(ea, dict):
                raise ValueError("ea_state reporter contiene un EA inválido")
            ea["sizing_pct"] = _decimal_json(ea.get("sizing_pct"))
    elif batch_type == "execution":
        fills = normalized.get("fills")
        if not isinstance(fills, list):
            raise ValueError("execution reporter sin lista fills")
        for fill in fills:
            if not isinstance(fill, dict):
                raise ValueError("execution reporter contiene un fill inválido")
            for field in ("volume", "requested_price", "executed_price", "spread"):
                fill[field] = _decimal_json(fill.get(field))
    return normalized


async def enqueue_reporter_outbox_once(
    buffer: Buffer,
    directory: str,
    account_login: str,
    connector_instance_id: str,
    filename_pattern: str = "*.jsonl",
) -> int:
    """Lee JSONL estables, valida su forma y los deja en el buffer SQLite.

    No renombra, borra, modifica ni ejecuta eventos del outbox de EA. Sólo
    acepta snapshots ``ea_state`` y fills ``execution`` para el login que
    opera este conector.
    """
    accepted = 0
    if not filename_pattern or Path(filename_pattern).name != filename_pattern:
        raise ValueError("filename_pattern debe ser un patrón de archivo local")
    for path in sorted(Path(directory).glob(filename_pattern)):
        raw_payload = path.read_text(encoding="utf-8")
        # Un EA puede estar terminando de escribir la última línea. Sólo se
        # procesan líneas con salto final; la siguiente lectura la verá ya
        # completa. El lector no renombra ni repara el fichero fuente.
        complete_lines = raw_payload.splitlines()
        if raw_payload and not raw_payload.endswith(("\n", "\r")):
            complete_lines = complete_lines[:-1]
        for raw_line in complete_lines:
            if not raw_line.strip():
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                # Una línea corrupta se rechaza localmente sin convertirla en
                # una orden ni alterar la procedencia; se conserva para inspección.
                continue
            batch_type = event.pop("batch_type", None)
            if batch_type not in {"ea_state", "execution"}:
                continue
            if event.get("account_login") != account_login:
                continue
            event = canonicalize_reporter_event(batch_type, event)
            event["connector_instance_id"] = connector_instance_id
            payload = _seal_and_serialize(account_login, batch_type, event)
            event_key = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if await buffer.enqueue_once(event_key, batch_type, payload):
                accepted += 1
    return accepted
