"""Registra un manifiesto explícito de adjunto demo ya realizado.

No abre MT5, no escribe perfiles, no compila EAs y no puede enviar órdenes.
Su única escritura, bajo ``--apply``, es append-only en StratOS.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import core.db.models  # noqa: F401
from core.db.base import async_session_factory
from core.db.models.pipeline import PipelineCandidate
from core.services.demo_attachment import DemoAttachmentManifest, register_demo_attachment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", type=int, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def run(value: argparse.Namespace) -> None:
    if not value.manifest.is_file():
        raise ValueError("demo attachment manifest does not exist")
    manifest = DemoAttachmentManifest.model_validate_json(
        value.manifest.read_text(encoding="utf-8")
    )
    async with async_session_factory() as session:
        candidate = await session.get(PipelineCandidate, value.candidate_id)
        if candidate is None:
            raise ValueError("candidate does not exist")
        attachment = await register_demo_attachment(
            session,
            candidate=candidate,
            manifest=manifest,
            source_path=value.manifest.resolve(),
        )
        payload = {
            "ok": True,
            "mode": "apply" if value.apply else "dry_run",
            "candidate_id": candidate.id,
            "attachment_id": attachment.id,
            "artifact_id": attachment.artifact_id,
            "next_action": "wait_for_sealed_reporter_ea_state",
        }
        if value.apply:
            await session.commit()
        else:
            await session.rollback()
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
