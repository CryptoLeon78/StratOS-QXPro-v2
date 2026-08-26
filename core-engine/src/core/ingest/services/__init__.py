"""Un modulo por endpoint de PARTE 9.1. Cada `ingest_x(session, account,
req) -> IngestOutcome` hace el trabajo real; la ruta en `router.py` solo
resuelve la cuenta, llama al servicio y comitea."""

from datetime import datetime
from typing import NamedTuple


class IngestOutcome(NamedTuple):
    accepted: int
    duplicated: int
    batch_id: int
    server_time: datetime  # IngestBatch.server_ts del mismo lote (PARTE 9.1)
