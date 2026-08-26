"""PARTE 12 (G4): buffer SQLite store-and-forward. El poller solo encola
(nunca depende de la red); `sender.py` (proxima unidad) es quien drena y
aplica backoff. `enqueue` es lo unico que hace que "corte de 10 min sin
perdidas" sea mecanicamente cierto: un poller nunca bloquea esperando a
que el servidor responda."""

from dataclasses import dataclass
from datetime import UTC, datetime

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT NOT NULL,
    last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_next_attempt ON outbox(next_attempt_at);
"""


def _utc_iso(dt: datetime) -> str:
    """`next_attempt_at`/`created_at` se comparan como TEXTO en SQLite (sin
    tipo DATETIME nativo) -- solo ordena cronologicamente si TODOS los
    valores estan normalizados al mismo offset. `.astimezone(UTC)` fuerza
    eso independientemente del huso horario del `datetime` recibido (debe
    venir con tzinfo; un naive se interpretaria como huso local del
    sistema, no UTC -- responsabilidad del caller)."""
    return dt.astimezone(UTC).isoformat()


@dataclass(frozen=True)
class OutboxRow:
    id: int
    batch_type: str
    payload_json: str
    attempts: int


class Buffer:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    @property
    def _connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Buffer.connect() no ha sido llamado")
        return self._conn

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        await self._connection.close()
        self._conn = None

    async def enqueue(self, batch_type: str, payload_json: str) -> int:
        now = _utc_iso(datetime.now(UTC))
        cursor = await self._connection.execute(
            "INSERT INTO outbox (batch_type, payload_json, created_at, next_attempt_at) "
            "VALUES (?, ?, ?, ?)",
            (batch_type, payload_json, now, now),
        )
        await self._connection.commit()
        row_id = cursor.lastrowid
        assert row_id is not None
        return row_id

    async def due_batches(self, now: datetime, limit: int) -> list[OutboxRow]:
        cursor = await self._connection.execute(
            "SELECT id, batch_type, payload_json, attempts FROM outbox "
            "WHERE next_attempt_at <= ? ORDER BY id ASC LIMIT ?",
            (_utc_iso(now), limit),
        )
        rows = await cursor.fetchall()
        return [OutboxRow(id=r[0], batch_type=r[1], payload_json=r[2], attempts=r[3]) for r in rows]

    async def mark_sent(self, row_id: int) -> None:
        await self._connection.execute("DELETE FROM outbox WHERE id = ?", (row_id,))
        await self._connection.commit()

    async def mark_failed(self, row_id: int, error: str, next_attempt_at: datetime) -> None:
        await self._connection.execute(
            "UPDATE outbox SET attempts = attempts + 1, last_error = ?, next_attempt_at = ? "
            "WHERE id = ?",
            (error, _utc_iso(next_attempt_at), row_id),
        )
        await self._connection.commit()

    async def get_meta(self, key: str) -> str | None:
        cursor = await self._connection.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row is not None else None

    async def set_meta(self, key: str, value: str) -> None:
        await self._connection.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await self._connection.commit()
