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


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_manifest(path: Path) -> tuple[dict[str, Any], str]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    supplied = manifest.pop("manifest_sha256", None)
    if not isinstance(supplied, str) or supplied != seal_payload(manifest):
        raise ValueError("sello de manifiesto inválido")
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
            bot = await session.scalar(
                select(Bot).where(Bot.account_id == account.id, Bot.magic_number == external_magic)
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
                    "range": manifest["range"],
                    "external_f7": (
                        {"account_login": external_account_login, "magic_number": external_magic}
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
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest, verdict = load_manifest(manifest_path)
    if not args.apply:
        print(f"verified run_id={manifest['run_id']} verdict={verdict}")
        return
    print(asyncio.run(persist(
        manifest, verdict, manifest_path, args.external_account_login, args.external_magic
    )))


if __name__ == "__main__":
    main()
