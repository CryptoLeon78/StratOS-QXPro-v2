"""Registra append-only un resultado sellado de SQX_vs_MT5.

Sólo un veredicto ``VALIDADA`` puede avanzar a ``BACKTEST_VALIDATED``. Cualquier
otro resultado conserva sus informes y queda ``WITHHELD``; esta herramienta no
crea bots, baselines ni adjunta EAs a la Incubadora.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import Any

VERDICT_PATTERN = re.compile(r"VEREDICTO:\s*(VALIDADA|TOLERABLE|DISCREPANTE)")


def resolve_external_magic(
    magic_number: int, identity_registry: Path | None
) -> tuple[int, bool]:
    """Traduce un magic anterior a la migración MN al vigente, si hace falta.

    La cola y los manifiestos F7 declaran los magics que los EAs emitían **antes** de la
    migración de identidad compacta; la tabla `bot` tiene los vigentes desde
    `sync_bot_magics_to_migration.py`. Registrar una corrida pasando el magic de la cola
    fallaba con "F7 externo no encontrado" aunque el bot existiera: dos fuentes hablando de
    lo mismo con identidades distintas.

    La traducción sale **exclusivamente** de los `legacy_magic_numbers` del registro
    append-only aprobado. Sin registro, o con un magic que el registro no conoce, se
    devuelve tal cual: no se inventa una correspondencia, y el fallo posterior conserva su
    mensaje propio en vez de resolverse a otro bot.

    Devuelve ``(magic, resuelto_por_traduccion)``; el segundo valor viaja a la evidencia
    para que la asociación quede auditable.
    """
    if identity_registry is None:
        return magic_number, False
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from magic_identity import build_legacy_magic_map

    destino = build_legacy_magic_map(identity_registry).get(magic_number)
    if destino is None:
        return magic_number, False
    return int(destino["magic_number"]), True


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_manifest(path: Path) -> tuple[dict[str, Any], str]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    supplied = manifest.pop("manifest_sha256", None)
    if not isinstance(supplied, str) or supplied != seal_payload(manifest):
        raise ValueError("sello de manifiesto inválido")
    cost_audit = manifest.get("cost_audit")
    cost_comparability = cost_audit.get("cost_comparability") if isinstance(cost_audit, dict) else None
    unsigned_cost_audit = (
        {key: value for key, value in cost_audit.items() if key != "audit_sha256"}
        if isinstance(cost_audit, dict) else None
    )
    cost_audit_hash_valid = (
        isinstance(cost_audit, dict)
        and isinstance(unsigned_cost_audit, dict)
        and cost_audit.get("audit_sha256") == seal_payload(unsigned_cost_audit)
    )
    mt5_cost_evidence = cost_comparability.get("mt5") if isinstance(cost_comparability, dict) else None
    separate_transaction_costs_valid = (
        isinstance(mt5_cost_evidence, dict)
        and all(
            isinstance(mt5_cost_evidence.get(key), dict)
            and mt5_cost_evidence[key].get("verified") is True
            for key in ("commission_evidence", "swap_evidence")
        )
    )
    combined_transaction_evidence = (
        mt5_cost_evidence.get("transaction_cost_evidence")
        if isinstance(mt5_cost_evidence, dict) else None
    )
    combined_transaction_costs_valid = (
        isinstance(combined_transaction_evidence, dict)
        and cost_comparability.get("transaction_cost_basis") == "SQX_COMBINED_COMM_SWAP_TOTAL"
        and combined_transaction_evidence.get("verified") is True
        and combined_transaction_evidence.get("aggregate_match") is True
        and combined_transaction_evidence.get("source_column") == "Comm/Swap"
        and combined_transaction_evidence.get("components_separated_by_sqx") is False
        and combined_transaction_evidence.get("full_trade_set_paired") is True
        and combined_transaction_evidence.get("matched_trades", 0) > 0
        and combined_transaction_evidence.get("sqx_trades") == combined_transaction_evidence.get("matched_trades")
        and combined_transaction_evidence.get("mt5_trades") == combined_transaction_evidence.get("matched_trades")
        and combined_transaction_evidence.get("matched_volume_equal") is True
        and combined_transaction_evidence.get("matched_direction_equal") is True
        and combined_transaction_evidence.get("trades_with_discrepancy") == 0
        and combined_transaction_evidence.get("maximum_absolute_trade_delta", float("inf")) <= 0.01
    )
    component_evidence_valid = (
        isinstance(mt5_cost_evidence, dict)
        and mt5_cost_evidence.get("spread_model") == "REAL_TICKS"
        and isinstance(mt5_cost_evidence.get("spread_evidence"), dict)
        and mt5_cost_evidence["spread_evidence"].get("verified") is True
        and (separate_transaction_costs_valid or combined_transaction_costs_valid)
    )
    reconciliation = cost_audit.get("empirical_reconciliation") if isinstance(cost_audit, dict) else None
    reconciliation_name = (
        reconciliation.get("path") if isinstance(reconciliation, dict) else None
    )
    reconciliation_artifact = next(
        (
            artifact for artifact in manifest.get("artifacts", [])
            if (
                PureWindowsPath(str(artifact.get("path", ""))).name
                if "\\" in str(artifact.get("path", ""))
                else Path(str(artifact.get("path", ""))).name
            ) == reconciliation_name
        ),
        None,
    )
    standard_reconciliation_source_valid = (
        isinstance(reconciliation, dict)
        and isinstance(reconciliation_artifact, dict)
        and reconciliation.get("path") == "cost-reconciliation.json"
        and reconciliation.get("sha256") == reconciliation_artifact.get("sha256")
        and reconciliation.get("status") == "PROVEN"
    )
    standard_cost_gate_valid = (
        isinstance(cost_comparability, dict)
        and cost_comparability.get("policy") == "REAL_MT5_TICKS_BLOCK_COST_DISCREPANCIES_V1"
        and cost_comparability.get("status") == "PROVEN"
        and cost_comparability.get("comparable") is True
        and component_evidence_valid
        and standard_reconciliation_source_valid
        and cost_comparability.get("mt5", {}).get("spread_model") == "REAL_TICKS"
    )
    sensitivity = (
        cost_comparability.get("current_tariff_sensitivity")
        if isinstance(cost_comparability, dict) else None
    )
    sensitivity_app = (
        sensitivity.get("tester_application") if isinstance(sensitivity, dict) else None
    )
    sensitivity_source = sensitivity.get("source") if isinstance(sensitivity, dict) else None
    sensitivity_rates = sensitivity.get("rates") if isinstance(sensitivity, dict) else None
    deal_export = sensitivity_app.get("deal_export") if isinstance(sensitivity_app, dict) else None
    source_snapshot = (
        sensitivity_source.get("snapshot_artifact")
        if isinstance(sensitivity_source, dict)
        else None
    )
    deal_artifact = next(
        (
            artifact for artifact in manifest.get("artifacts", [])
            if (
                PureWindowsPath(str(artifact.get("path", ""))).name
                if "\\" in str(artifact.get("path", ""))
                else Path(str(artifact.get("path", ""))).name
            ) == "mt5-deals.csv"
        ),
        None,
    )
    source_snapshot_artifact = next(
        (
            artifact for artifact in manifest.get("artifacts", [])
            if (
                PureWindowsPath(str(artifact.get("path", ""))).name
                if "\\" in str(artifact.get("path", ""))
                else Path(str(artifact.get("path", ""))).name
            ) == "broker-tariff-snapshot.json"
        ),
        None,
    )
    try:
        if not isinstance(sensitivity, dict) or not isinstance(sensitivity_source, dict):
            raise ValueError("missing sensitivity metadata")
        from datetime import date

        scenario_date = date.fromisoformat(str(sensitivity.get("scenario_as_of")))
        published_at = datetime.fromisoformat(
            str(sensitivity_source.get("published_at", "")).replace("Z", "+00:00")
        )
        run_time = datetime.fromisoformat(
            str(manifest.get("generated_at_utc", "")).replace("Z", "+00:00")
        )
        scenario_dates_valid = (
            published_at.tzinfo is not None
            and run_time.tzinfo is not None
            and published_at.date() <= scenario_date <= run_time.date()
        )
    except (TypeError, ValueError):
        scenario_dates_valid = False
    sensitivity_artifact = (
        isinstance(reconciliation, dict)
        and isinstance(reconciliation_artifact, dict)
        and reconciliation.get("path") == "sensitivity-reconciliation.json"
        and reconciliation.get("status") == "SCENARIO_VALIDATED"
        and reconciliation.get("sha256") == reconciliation_artifact.get("sha256")
    )
    parent_artifact = next(
        (
            artifact for artifact in manifest.get("artifacts", [])
            if (
                PureWindowsPath(str(artifact.get("path", ""))).name
                if "\\" in str(artifact.get("path", ""))
                else Path(str(artifact.get("path", ""))).name
            ) == "parent-run-manifest.json"
        ),
        None,
    )
    try:
        sensitivity_path = path.parent / str(reconciliation.get("path", ""))
        sensitivity_payload = json.loads(sensitivity_path.read_text(encoding="utf-8"))
        parent_path = path.parent / "parent-run-manifest.json"
        parent_manifest = json.loads(parent_path.read_text(encoding="utf-8"))
        source_snapshot_path = path.parent / str(source_snapshot.get("path", ""))
        source_snapshot_payload = json.loads(source_snapshot_path.read_text(encoding="utf-8"))
        expected_source = {
            key: value for key, value in sensitivity_source.items()
            if key != "snapshot_artifact"
        }
        source_snapshot_valid = (
            source_snapshot_payload.get("scenario_as_of") == sensitivity.get("scenario_as_of")
            and source_snapshot_payload.get("instrument") == sensitivity.get("instrument")
            and source_snapshot_payload.get("source") == expected_source
            and source_snapshot_payload.get("rates") == sensitivity_rates
        )
        parent_unsigned = {
            key: value for key, value in parent_manifest.items() if key != "manifest_sha256"
        }
        parent_payload_valid = (
            parent_manifest.get("manifest_sha256") == seal_payload(parent_unsigned)
            and parent_manifest.get("manifest_sha256")
            == manifest.get("sensitivity_parent_manifest_sha256")
            and parent_artifact is not None
            and hashlib.sha256(parent_path.read_bytes()).hexdigest()
            == parent_artifact.get("sha256")
            and sensitivity_payload == sensitivity
            and source_snapshot_valid
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        parent_payload_valid = False
    current_tariff_sensitivity_valid = (
        isinstance(cost_comparability, dict)
        and cost_comparability.get("policy") == "CURRENT_TARIFF_SENSITIVITY_V1"
        and cost_comparability.get("status") == "SCENARIO_VALIDATED"
        and cost_comparability.get("comparable") is True
        and cost_comparability.get("transaction_cost_basis") == "CURRENT_BROKER_TARIFF_SCENARIO"
        and isinstance(sensitivity, dict)
        and sensitivity.get("schema_version") == 1
        and sensitivity.get("scenario") == "CURRENT_BROKER_TARIFF_SENSITIVITY"
        and scenario_dates_valid
        and sensitivity.get("instrument") == manifest.get("strategy", {}).get("symbol")
        and isinstance(sensitivity_source, dict)
        and "darwinex.com" in str(sensitivity_source.get("url", "")).casefold()
        and isinstance(source_snapshot, dict)
        and source_snapshot.get("path") == "broker-tariff-snapshot.json"
        and isinstance(source_snapshot_artifact, dict)
        and source_snapshot.get("sha256") == source_snapshot_artifact.get("sha256")
        and isinstance(sensitivity_rates, dict)
        and isinstance(sensitivity_rates.get("commission_per_order_per_contract"), dict)
        and sensitivity_rates["commission_per_order_per_contract"].get("value", 0) > 0
        and sensitivity_rates["commission_per_order_per_contract"].get("currency") == "AUD"
        and isinstance(sensitivity_rates.get("swap_long_per_contract_per_day"), dict)
        and sensitivity_rates["swap_long_per_contract_per_day"].get("value", 0) > 0
        and sensitivity_rates["swap_long_per_contract_per_day"].get("currency") == "CAD"
        and isinstance(sensitivity_app, dict)
        and sensitivity_app.get("mode") == "MT5_STRATEGY_TESTER"
        and sensitivity_app.get("price_model") == "REAL_TICKS"
        and sensitivity_app.get("range") == manifest.get("range")
        and sensitivity_app.get("sqx_cost_equivalence_claimed") is False
        and isinstance(sensitivity_app.get("closed_positions"), int)
        and sensitivity_app.get("closed_positions", 0) > 0
        and isinstance(deal_export, dict)
        and deal_export.get("path") == "mt5-deals.csv"
        and isinstance(deal_artifact, dict)
        and deal_export.get("sha256") == deal_artifact.get("sha256")
        and sensitivity.get("parent_manifest_sha256") == manifest.get("sensitivity_parent_manifest_sha256")
        and parent_payload_valid
        and isinstance(manifest.get("sensitivity_parent_manifest_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", manifest.get("sensitivity_parent_manifest_sha256", "")) is not None
        and sensitivity_app.get("closed_positions") == sensitivity_app.get("exported_closed_positions")
        and sensitivity_artifact
        and isinstance(mt5_cost_evidence, dict)
        and mt5_cost_evidence.get("spread_model") == "REAL_TICKS"
        and isinstance(mt5_cost_evidence.get("spread_evidence"), dict)
        and mt5_cost_evidence["spread_evidence"].get("verified") is True
    )
    cost_gate_valid = standard_cost_gate_valid or current_tariff_sensitivity_valid
    if (
        not cost_audit_hash_valid
        or not cost_gate_valid
        or not isinstance(cost_audit.get("source"), dict)
        or cost_audit["source"].get("sqx_sha256") != manifest.get("source", {}).get("sqx_sha256")
    ):
        raise ValueError("comparabilidad de costes no probada para el SQX exacto; BACKTEST_VALIDATED bloqueado")
    if manifest.get("mode") != "launch" or manifest.get("result", {}).get("returncode") != 0:
        raise ValueError("el manifiesto no acredita un backtest terminado correctamente")
    verdict = VERDICT_PATTERN.search(str(manifest["result"].get("stdout", "")))
    if verdict is None:
        raise ValueError("no se encontró veredicto SQX_vs_MT5 en la evidencia")
    for artifact in manifest.get("artifacts", []):
        raw_path = str(artifact["path"])
        artifact_path = Path(raw_path)
        if not artifact_path.is_file():
            # El manifiesto conserva la ruta de origen Windows; dentro del
            # contenedor operacional el directorio sellado se monta en /runtime.
            artifact_name = PureWindowsPath(raw_path).name if "\\" in raw_path else artifact_path.name
            artifact_path = path.parent / artifact_name
        if not artifact_path.is_file():
            raise ValueError(f"artefacto ausente: {artifact_path}")
        digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if digest != artifact["sha256"]:
            raise ValueError(f"hash inválido: {artifact_path.name}")
        artifact["path"] = str(artifact_path)
    manifest["manifest_sha256"] = supplied
    return manifest, verdict.group(1)


async def persist(
    manifest: dict[str, Any],
    verdict: str,
    manifest_path: Path,
    external_account_login: str | None = None,
    external_magic: int | None = None,
    identity_registry: Path | None = None,
) -> str:
    from core.config import get_settings
    from core.db.base import async_session_factory
    from core.db.enums import AssetAdmissionStatus, AssetSourceGroup, BotOriginKind
    from core.db.models.accounts import Account, Bot
    from core.db.models.operations import OperationalAsset, OperationalAssetEvent
    from core.services.admin_imports import _get_or_create_artifact
    from sqlalchemy import select

    if get_settings().deployment_profile != "operational":
        raise ValueError("sólo se permite registrar backtests en perfil operational")
    if (external_account_login is None) != (external_magic is None):
        raise ValueError("la cuenta y el magic F7 externo deben declararse juntos")
    source = manifest["source"]
    async with async_session_factory() as session:
        asset = (
            await session.execute(
                select(OperationalAsset).where(
                    OperationalAsset.sqx_sha256 == source["sqx_sha256"],
                    OperationalAsset.mql5_sha256 == source["mq5_sha256"],
                )
            )
        ).scalar_one_or_none()
        if asset is None and external_account_login is None:
            raise ValueError("fuente no inventariada; no se asocia por nombre")
        if external_account_login is not None:
            account = await session.scalar(
                select(Account).where(Account.login == external_account_login)
            )
            # La cola declara magics anteriores a la migracion MN y la base ya tiene los
            # vigentes: se traduce antes de buscar, y se deja constancia de por que via se
            # resolvio (backlog A25).
            resolved_magic, resolved_via_legacy = resolve_external_magic(
                int(external_magic), identity_registry
            )
            bot = await session.scalar(
                select(Bot).where(Bot.account_id == account.id, Bot.magic_number == resolved_magic)
            ) if account is not None else None
            if bot is None or bot.origin_kind != BotOriginKind.EXTERNAL_PRODUCTION:
                raise ValueError("F7 externo no encontrado por cuenta y magic exactos")
            if asset is None:
                asset = OperationalAsset(
                    source_group=AssetSourceGroup.REAL,
                    source_root=str(manifest_path.parent),
                    sqx_path=source["sqx_path"], mql5_path=source["mq5_path"],
                    sqx_sha256=source["sqx_sha256"], mql5_sha256=source["mq5_sha256"],
                    strategy_name=bot.name, magic_number=bot.magic_number,
                    symbol=bot.market, timeframe=bot.timeframe, discovered_at=datetime.now(UTC),
                )
                session.add(asset)
                await session.flush()
        previous = (
            await session.execute(
                select(OperationalAssetEvent).where(OperationalAssetEvent.asset_id == asset.id)
            )
        ).scalars()
        if any(event.evidence.get("run_id") == manifest["run_id"] for event in previous):
            return "already_recorded"

        artifact_ids: list[int] = []
        for entry in manifest["artifacts"]:
            artifact_path = Path(entry["path"])
            artifact = await _get_or_create_artifact(
                session,
                kind="SQX_MT5_REPORT",
                path=artifact_path,
                payload=artifact_path.read_bytes(),
                parser_version="sqx-vs-mt5-v1",
                metadata={"run_id": manifest["run_id"], "sha256": entry["sha256"]},
            )
            artifact_ids.append(artifact.id)
        manifest_artifact = await _get_or_create_artifact(
            session,
            kind="SQX_MT5_MANIFEST",
            path=manifest_path,
            payload=manifest_path.read_bytes(),
            parser_version="operational-run-manifest-v1",
            metadata={"run_id": manifest["run_id"], "verdict": verdict},
        )
        status = (
            AssetAdmissionStatus.BACKTEST_VALIDATED
            if verdict == "VALIDADA"
            else AssetAdmissionStatus.WITHHELD
        )
        if external_account_login is not None:
            status = AssetAdmissionStatus.WITHHELD
        session.add(
            OperationalAssetEvent(
                asset_id=asset.id,
                status=status,
                reason=(
                    f"EXTERNAL_F7_SQX_MT5_{verdict}"
                    if external_account_login is not None
                    else (None if verdict == "VALIDADA" else f"SQX_MT5_{verdict}")
                ),
                evidence={
                    "run_id": manifest["run_id"],
                    "manifest_sha256": manifest["manifest_sha256"],
                    "manifest_artifact_id": manifest_artifact.id,
                    "artifact_ids": artifact_ids,
                    "verdict": verdict,
                    "validation_mode": manifest["cost_audit"]["cost_comparability"]["policy"],
                    "current_tariff_sensitivity": manifest["cost_audit"]["cost_comparability"].get(
                        "current_tariff_sensitivity"
                    ),
                    "range": manifest["range"],
                    "external_f7": (
                        {
                            "account_login": external_account_login,
                            "magic_number": resolved_magic,
                            "declared_magic_number": external_magic,
                            "resolved_via_legacy_magic": resolved_via_legacy,
                        }
                        if external_account_login is not None else None
                    ),
                },
                occurred_at=datetime.now(UTC),
            )
        )
        await session.commit()
    return f"asset_id={asset.id} status={status.value} verdict={verdict}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--external-account-login")
    parser.add_argument("--external-magic", type=int)
    parser.add_argument(
        "--identity-registry",
        type=Path,
        default=None,
        help=(
            "registro append-only de identidad; traduce un magic anterior a la migracion MN "
            "al vigente antes de buscar el bot F7. Sin el, el magic se usa tal cual."
        ),
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest, verdict = load_manifest(manifest_path)
    if not args.apply:
        print(f"verified run_id={manifest['run_id']} verdict={verdict}")
        return
    print(asyncio.run(persist(
        manifest,
        verdict,
        manifest_path,
        args.external_account_login,
        args.external_magic,
        args.identity_registry,
    )))


if __name__ == "__main__":
    main()
