import sqlite3
from pathlib import Path

from scripts.requeue_g12_reporter_events import requeue


def test_requeue_removes_only_reporter_dedup_keys(tmp_path: Path) -> None:
    buffer = tmp_path / "connector-buffer.sqlite"
    with sqlite3.connect(buffer) as connection:
        connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO meta VALUES ('reporter_event:a', 'x')")
        connection.execute("INSERT INTO meta VALUES ('last_deal_ts', 'x')")
        connection.commit()

    payload = requeue(buffer, tmp_path / "report.json", apply=True)

    assert payload["reporter_dedup_keys_before"] == 1
    assert payload["reporter_dedup_keys_after"] == 0
    with sqlite3.connect(buffer) as connection:
        assert connection.execute("SELECT value FROM meta WHERE key = 'last_deal_ts'").fetchone() == ("x",)
