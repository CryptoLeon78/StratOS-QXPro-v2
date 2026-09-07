"""Read-only observation readiness evidence; never logs credentials or creates a session."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

# Fixed schema identifiers. Values are aggregate evidence, never credentials or trade details.
OBSERVATION_SQL = """
SELECT json_build_object(
 'database_time', now(),
 'counts', json_build_object(
   'accounts',(SELECT count(*) FROM account),
   'bots',(SELECT count(*) FROM bot),
   'trades',(SELECT count(*) FROM trade),
   'ingest_batches',(SELECT count(*) FROM ingest_batch),
   'alerts',(SELECT count(*) FROM alert),
   'fx_rates',(SELECT count(*) FROM fx_rate)),
 'operator_hash_prefix', (SELECT bool_and(hashed_password LIKE '$argon2%')
                       FROM "user" WHERE role = 'operator'),
 'freshness_threshold', (SELECT value FROM system_config
                        WHERE key = 'header_heartbeat_stale_after_s'),
 'real_accounts', (SELECT json_agg(json_build_object(
   'account_id', a.id,
   'heartbeat_age_seconds', (SELECT extract(epoch FROM now()-max(h.ts))
                            FROM heartbeat_log h WHERE h.account_id=a.id),
   'equity_age_seconds', (SELECT extract(epoch FROM now()-max(e.ts))
                         FROM equity_snapshot e WHERE e.account_id=a.id)))
 FROM account a WHERE a.is_active AND a.data_origin='BROKER_REAL'));
"""


def query_database(container: str, timeout: float) -> dict[str, Any]:
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            container,
            "sh",
            "-c",
            'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At',
        ],
        input=OBSERVATION_SQL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("database_read_failed")
    return json.loads(result.stdout)


def telemetry_ready(accounts: list[dict[str, Any]], threshold: float) -> bool:
    """Require both streams for EVERY real account; a healthy demo cannot mask a real outage."""
    return bool(accounts) and all(
        isinstance(row.get(field), (float, int)) and 0 <= row[field] <= threshold
        for row in accounts
        for field in ("heartbeat_age_seconds", "equity_age_seconds")
    )


def http_status(url: str, timeout: float) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError):
        return None


def check(config: dict[str, Any]) -> dict[str, Any]:
    timeout = config["timeout_seconds"]
    services = {}
    for service in config["services"]:
        container = f"{config['compose_project']}-{service}-1"
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}",
                container,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        parts = result.stdout.strip().split("|")
        services[service] = {
            "running": result.returncode == 0 and parts[0] == "running",
            "restart_policy": parts[1] if len(parts) == 2 else None,
        }
    public_http = {url: http_status(url, timeout) for url in config["public_urls"]}
    protected_status = http_status(config["protected_url"], timeout)
    database: dict[str, Any] = {}
    database_error = None
    try:
        database = query_database(config["postgres_container"], timeout)
    except (RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        database_error = type(exc).__name__
    seed = json.loads((REPO_ROOT / config["thresholds_path"]).read_text(encoding="utf-8"))
    threshold = database.get("freshness_threshold")
    if threshold is None:
        threshold = seed["header_heartbeat_stale_after_s"]
    gates = {
        "services_running": all(row["running"] for row in services.values()),
        "automatic_restart": all(
            row["restart_policy"] == "unless-stopped" for row in services.values()
        ),
        "public_http": all(status == 200 for status in public_http.values()),
        "anonymous_access_rejected": protected_status == 401,
        "database_readable": database_error is None,
        "operator_hash_prefix": database.get("operator_hash_prefix") is True,
        "real_telemetry_fresh": telemetry_ready(database.get("real_accounts") or [], threshold),
    }
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "scope": "read_only_observation_preflight",
        "status": "PREFLIGHT_PASS" if all(gates.values()) else "BLOCKED",
        "gates": gates,
        "services": services,
        "public_http": public_http,
        "protected_http": protected_status,
        "database": database,
        "database_error": database_error,
        "freshness_threshold_seconds": threshold,
        "not_verified": [
            "operator_login",
            "authenticated_browser",
            "websocket_delivery",
            "alert_delivery",
            "backup_restore",
            "host_reboot",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config/observation_check.json")
    args = parser.parse_args()
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    report = check(config)
    report["config_sha256"] = hashlib.sha256(config_bytes).hexdigest()
    report["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output_dir = REPO_ROOT / config["output_directory"]
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    report["run_id"] = run_id
    payload = json.dumps(report, indent=2, sort_keys=True).encode("utf-8")
    output = output_dir / f"observation-{run_id}.json"
    output.write_bytes(payload)
    output.with_suffix(".sha256").write_text(hashlib.sha256(payload).hexdigest(), encoding="ascii")
    print(json.dumps({"status": report["status"], "gates": report["gates"], "report": str(output)}))
    return 0 if report["status"] == "PREFLIGHT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
