"""Back up the configured database and restore into a NEW verification database.

No dotenv or credential reads. Docker uses its configured PostgreSQL environment.
Never drops an existing database: only the verification database created by this run.
Timescale pre/post restore hooks are required; restore errors fail the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from check_observation import REPO_ROOT


def canonical_constraints(
    rows: list[dict[str, str]], equivalences: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Accept only reviewed, EXACT deparser rewrites, never strip arbitrary casts."""
    canonical = []
    for row in rows:
        normalized = dict(row)
        for rule in equivalences:
            if (
                row["table_name"] == rule["table_name"]
                and row["constraint_name"] == rule["constraint_name"]
                and row["definition"] == rule["restored"]
            ):
                normalized["definition"] = rule["source"]
        canonical.append(normalized)
    return canonical


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config/observation_check.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ").lower()
    verify_db = f"stratos_verify_{run_id}"
    output = REPO_ROOT / config["output_directory"] / f"backup-{run_id}"
    output.mkdir(parents=True, exist_ok=False)
    container = config["postgres_container"]
    remote_dump = f"/tmp/{verify_db}.dump"
    commands: list[dict[str, Any]] = []

    def execute(command: str, *params: str, sql: str | None = None) -> str:
        result = subprocess.run(
            ["docker", "exec", "-i", container, "sh", "-c", command, "sh", *params],
            input=sql,
            capture_output=True,
            text=True,
            check=False,
            timeout=config["backup_step_timeout_seconds"],
        )
        commands.append({"step": len(commands) + 1, "returncode": result.returncode})
        if result.returncode:
            # Do not print subprocess output: failures may contain deployment details.
            raise RuntimeError(f"backup_step_{len(commands)}_failed")
        return result.stdout.strip()

    def query(sql: str, database: str | None = None) -> str:
        return execute(
            'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${1:-$POSTGRES_DB}" -At',
            database or "",
            sql=sql,
        )

    def counts(database: str | None = None) -> dict[str, int]:
        tables = json.loads(
            query(
                "SELECT json_agg(tablename ORDER BY tablename) FROM pg_tables "
                "WHERE schemaname='public';",
                database,
            )
        )
        result = {}
        for table in tables:
            identifier = '"' + table.replace('"', '""') + '"'
            result[table] = int(query(f"SELECT count(*) FROM public.{identifier};", database))
        return result

    schema_sql = """
    SELECT json_agg(row_to_json(s) ORDER BY s.table_name,s.constraint_name) FROM (
      SELECT c.relname AS table_name,con.conname AS constraint_name,
             pg_get_constraintdef(con.oid) AS definition
      FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
      JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
    ) s;
    """
    report: dict[str, Any] = {"run_id": run_id, "status": "FAILED", "commands": commands}
    created = False
    try:
        before = counts()
        constraints = json.loads(query(schema_sql))
        execute('pg_dump -U "$POSTGRES_USER" -Fc -f "$1" "$POSTGRES_DB"', remote_dump)
        dump = output / "database.dump"
        subprocess.run(
            ["docker", "cp", f"{container}:{remote_dump}", str(dump)],
            check=True,
            capture_output=True,
            timeout=config["backup_step_timeout_seconds"],
        )
        report["dump_sha256"] = hashlib.sha256(dump.read_bytes()).hexdigest()
        report["dump_bytes"] = dump.stat().st_size
        execute('createdb -U "$POSTGRES_USER" "$1"', verify_db)
        created = True
        query(
            "CREATE EXTENSION IF NOT EXISTS timescaledb; SELECT timescaledb_pre_restore();",
            verify_db,
        )
        execute(
            'pg_restore --exit-on-error -U "$POSTGRES_USER" -d "$1" "$2"', verify_db, remote_dump
        )
        query("SELECT timescaledb_post_restore();", verify_db)
        restored = counts(verify_db)
        after = counts()
        restored_constraints = json.loads(query(schema_sql, verify_db))
        report["source_constraints"] = constraints
        report["restored_constraints"] = restored_constraints
        equivalences = config.get("constraint_equivalences", [])
        report.update(
            {
                "source_counts_before": before,
                "source_counts_after": after,
                "restored_counts": restored,
                "counts_match": before == after == restored,
                "constraints_raw_match": constraints == restored_constraints,
                "constraints_match": canonical_constraints(constraints, equivalences)
                == canonical_constraints(restored_constraints, equivalences),
            }
        )
        if report["counts_match"] and report["constraints_match"]:
            report["status"] = "PASS"
    except (RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        report["failure"] = type(exc).__name__
    finally:
        if created:
            try:
                execute('dropdb -U "$POSTGRES_USER" "$1"', verify_db)
                report["verification_database_removed"] = True
            except (RuntimeError, subprocess.SubprocessError):
                report["verification_database_removed"] = False
                report["status"] = "FAILED"
        try:
            execute('rm -f -- "$1"', remote_dump)
            report["temporary_dump_removed"] = True
        except (RuntimeError, subprocess.SubprocessError):
            report["temporary_dump_removed"] = False
            report["status"] = "FAILED"
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report["config_sha256"] = hashlib.sha256(args.config.read_bytes()).hexdigest()
        payload = json.dumps(report, indent=2, sort_keys=True).encode()
        (output / "manifest.json").write_bytes(payload)
        (output / "manifest.sha256").write_text(
            hashlib.sha256(payload).hexdigest(), encoding="ascii"
        )
    print(json.dumps({"status": report["status"], "evidence": str(output)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
