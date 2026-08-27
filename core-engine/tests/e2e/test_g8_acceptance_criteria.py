"""PARTE 16 -- criterios de aceptación automatizables verificados contra el
seed real de PARTE 13 (`scripts/seed.py --profile ci|full --reset`, ya
corrido ANTES de esta suite -- ver `.github/workflows/ci.yml`, jobs
`e2e-playwright`/`e2e-acceptance-full`). A diferencia del resto de
`tests/e2e/`, este archivo NO usa el sandbox `stratos_test` (migrado en
limpio, sin datos): lee la base de datos REAL ya sembrada, apuntada por
`DATABASE_URL`/`APP_DATABASE_URL` del entorno -- exactamente como se
ejecutaría en CI. Localmente: sembrar primero
(`python scripts/seed.py --profile ci --reset`), luego
`pytest core-engine/tests/e2e/test_g8_acceptance_criteria.py`.

`_session()` crea un engine NUEVO por test en vez de reutilizar el
singleton de módulo `core.db.base.async_session_factory` -- ese singleton
se crea una sola vez atado al event loop vigente en ese momento, y
pytest-asyncio (modo `auto`, sin `loop_scope` fijado) da un event loop
NUEVO a cada función de test; reutilizarlo revienta con "Event loop is
closed" a partir del segundo test (hallazgo real, verificado en este
commit). Mismo motivo por el que `tests/conftest.py::db_connection` crea
su propio engine en vez de importar el de la app.

Índice de los 17 criterios (los no listados aquí ya están cubiertos en
otro sitio, ver referencias):

1  Cabecera <2s: `frontend/e2e/resumen.spec.ts` (G6) + `header_state.py`
   (assert final del propio seed).
2  Poseidón NARANJA + Decision: `test_criterion_2_*` (este archivo).
3  crash_21 L1->L4 + sin desescalado sin firma + histéresis:
   `tests/services/test_killswitch_sweep.py::test_crash_21_style_drop_can_jump_directly_to_l4`
   + `tests/state_machines/test_killswitch.py` (histéresis + property
   "nunca desescala sin firma", G3).
4  Cementerio 409: `tests/routers/test_cemetery.py::test_always_returns_409`.
5  Impulso pendiente cierra a 7 días: `test_criterion_5_*` (este archivo).
6  Auditoría limpia / --inject-audit-error -> CRITICA: `test_criterion_6_*`.
7  Watchdog muerto/desbocado/OK: `test_criterion_7_*`.
8  Huérfanos listados + reenvío no duplica + sello verifica: `test_criterion_8_*`.
9  Lyra x Phoenix redundante: `test_criterion_9_*` (solo perfil `full`).
10 Estige HOLD / Sigma GO / Promover bloqueado: `test_criterion_10_*`.
11 SIZING_CAP: `tests/services/test_staging.py::TestEscalateStagingStep::
   test_sizing_cap_blocks_escalation_above_89_percent`.
12 Posición sin SL -> Telegram <60s: `tests/e2e/test_g5_exit_criteria.py`.
13 Corte 10min sin pérdidas/duplicados: `integration-tests/tests/
   test_connector_core_integration.py::test_outage_then_recovery_zero_loss_zero_duplicates`
   (G4). El badge "DATOS STALE" es cálculo puro sobre `HeartbeatLog.ts`
   (`routers/header.py`, ya cubierto por `resumen.spec.ts`), sin lógica
   nueva que testear aquí.
14 Vista dominical sin rentabilidad: Playwright (pendiente, commit posterior).
15 Screenshot-diff 10 pestañas: Playwright (pendiente, commit posterior).
16 scan_hardcoding: procedimiento manual, PHASE REPORT.
17 docker compose up + seed <10min: procedimiento manual, PHASE REPORT.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from ingest_seal.sealing import SealMismatchError, compute_batch_sha256
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings
from core.db.enums import ImpulseStatus, SemaphoreState, Verdict
from core.db.models.accounts import Account, Bot
from core.db.models.decisions import Alert, Decision, ImpulseLog
from core.db.models.governance import CorrelationMatrix, SystemConfig
from core.db.models.market import EquitySnapshot, Trade
from core.db.models.pipeline import PipelineCandidate
from core.ingest.schemas import TradeIn, TradesIngestRequest
from core.ingest.services.trades import ingest_trades
from core.redis import get_redis_client
from core.routers.pipeline import promote_candidate
from core.services.audit import AuditConfig, run_audit_daily
from core.services.watchdog import WatchdogServiceConfig, evaluate_all_bots


@asynccontextmanager
async def _session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().app_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


async def _prod_account(session: AsyncSession) -> Account:
    return (
        await session.execute(select(Account).where(Account.login == "stratos-prod-1"))
    ).scalar_one()


async def _seed_profile(session: AsyncSession) -> str | None:
    row = (
        await session.execute(select(SystemConfig).where(SystemConfig.key == "seed_profile"))
    ).scalar_one_or_none()
    return row.value.get("profile") if row else None


async def test_criterion_2_poseidon_naranja_con_decision_pendiente() -> None:
    async with _session() as session:
        bot = (
            await session.execute(select(Bot).where(Bot.name == "Poseidón Trend GER40"))
        ).scalar_one()
        assert bot.semaphore_state == SemaphoreState.NARANJA
        assert bot.sizing_current_pct == Decimal("50.00")

        decision = (
            await session.execute(
                select(Decision).where(
                    Decision.module == "semaphore",
                    Decision.title.like("Poseid%NARANJA"),
                )
            )
        ).scalar_one()
        assert decision.status.value == "PENDING"
        assert decision.instruction_text == (
            f"En el EA magic {bot.magic_number}: desactivar apertura de nuevas "
            "posiciones (modo paper) y dejar cerrar las existentes por sus reglas."
        )


async def test_criterion_5_impulso_pendiente_cierra_a_7_dias() -> None:
    async with _session() as session:
        impulses = (await session.execute(select(ImpulseLog))).scalars().all()

        pending = [i for i in impulses if i.status == ImpulseStatus.PENDING]
        closed = [i for i in impulses if i.status == ImpulseStatus.CLOSED]
        assert len(pending) == 1, "se esperaba exactamente 1 impulso PENDING (<7 días)"
        assert len(closed) >= 3, "se esperaban >=3 impulsos CLOSED (>7 días)"

        for impulse in closed:
            assert impulse.avoided_cost_eur is not None
            assert impulse.evaluated_at is not None
        assert pending[0].avoided_cost_eur is None
        assert pending[0].status == ImpulseStatus.PENDING


async def test_criterion_6_auditoria_limpia_y_inject_error_dispara_critica() -> None:
    async with _session() as session:
        existing = (
            await session.execute(
                select(func.count(Alert.id)).where(
                    Alert.module == "audit", Alert.resolved.is_(False)
                )
            )
        ).scalar_one()
        assert existing == 0, "se esperaba auditoría limpia antes de inyectar el error"

        prod = await _prod_account(session)
        # Misma perturbacion que `--inject-audit-error`
        # (scripts/seed_lib/audit_error.py) -- reimplementada aqui en vez
        # de importar cruzando el paquete `scripts/` (core-engine/tests/
        # no depende de scripts/, es al reves) para probar ambas ramas
        # de la auditoria en un solo test sin resembrar dos veces.
        last_ts = (
            await session.execute(
                select(EquitySnapshot.ts)
                .where(EquitySnapshot.account_id == prod.id)
                .order_by(EquitySnapshot.ts.desc())
                .limit(1)
            )
        ).scalar_one()
        await session.execute(
            update(EquitySnapshot)
            .where(EquitySnapshot.account_id == prod.id, EquitySnapshot.ts == last_ts)
            .values(balance=EquitySnapshot.balance + 100)
        )
        await session.commit()

        redis = get_redis_client()
        await run_audit_daily(session, redis, AuditConfig(), datetime.now(UTC))
        await session.commit()

        alert = (
            await session.execute(
                select(Alert).where(Alert.module == "audit", Alert.resolved.is_(False))
            )
        ).scalar_one()
        assert alert.level.value == "CRITICA"
        assert "descuadre" in alert.message


async def test_criterion_7_watchdog_muerto_desbocado_ok() -> None:
    async with _session() as session:
        now = datetime.now(UTC)
        rows = await evaluate_all_bots(session, WatchdogServiceConfig(), now)
        bots = {b.id: b.name for b in (await session.execute(select(Bot))).scalars().all()}
        by_name = {bots[r.bot_id]: r for r in rows if r.bot_id in bots}

        assert by_name["Hipnos Grid US30"].state.value == "DEAD"
        assert by_name["Hipnos Grid US30"].observed_30d == 0
        assert by_name["Baco Scalper GBPUSD"].state.value == "RUNAWAY"
        assert by_name["Atlas Trend EURUSD"].state.value == "OK"
        assert by_name["Lyra Scalper EURUSD"].state.value == "OK"

        ok_count = sum(1 for r in by_name.values() if r.state.value == "OK")
        assert ok_count >= 28, f"se esperaban >=28 bots OK, hubo {ok_count}"


async def test_criterion_8_huerfanos_listados() -> None:
    async with _session() as session:
        prod = await _prod_account(session)
        n_orphans = (
            await session.execute(
                select(func.count(Trade.id)).where(
                    Trade.account_id == prod.id, Trade.bot_id.is_(None)
                )
            )
        ).scalar_one()
        assert n_orphans >= 3


async def test_criterion_8_reenvio_de_trade_no_duplica() -> None:
    async with _session() as session:
        prod = await _prod_account(session)
        existing = (
            await session.execute(
                select(Trade)
                .where(
                    Trade.account_id == prod.id,
                    Trade.bot_id.is_not(None),
                    Trade.close_time.is_not(None),
                )
                .limit(1)
            )
        ).scalar_one()
        assert existing.close_time is not None

        trade_in = TradeIn(
            ticket_mt5=existing.ticket_mt5,
            symbol=existing.symbol,
            magic_number=existing.magic_number,
            type=existing.type,
            volume=existing.volume,
            open_time=existing.open_time,
            close_time=existing.close_time,
            open_price=existing.open_price,
            close_price=existing.close_price or existing.open_price,
            sl=existing.sl,
            tp=existing.tp,
            profit=existing.profit,
            commission=existing.commission,
            swap=existing.swap,
        )
        # El sello real se calcula sobre TODO el request menos batch_sha256
        # (core/ingest/batch.py) -- se reconstruye igual que el router.
        req = TradesIngestRequest(
            account_login=prod.login,
            connector_instance_id=prod.connector_instance_id or "test",
            trades=[trade_in],
            batch_sha256="0" * 64,
        )
        real_payload = [req.model_dump(mode="json", exclude={"batch_sha256"})]
        req.batch_sha256 = compute_batch_sha256(prod.login, "trades", real_payload)

        before = (await session.execute(select(func.count(Trade.id)))).scalar_one()
        outcome = await ingest_trades(session, prod, req)
        await session.commit()
        after = (await session.execute(select(func.count(Trade.id)))).scalar_one()

        assert outcome.accepted == 0
        assert outcome.duplicated == 1
        assert after == before, "el reenvío no debe crear filas nuevas"


async def test_criterion_8_sello_sha256_verifica() -> None:
    async with _session() as session:
        prod = await _prod_account(session)
        trade_in = TradeIn(
            ticket_mt5=9_999_999,
            symbol="EURUSD",
            magic_number=118231,
            type="BUY",  # type: ignore[arg-type]
            volume=Decimal("0.10"),
            open_time=datetime.now(UTC),
            close_time=datetime.now(UTC),
            open_price=Decimal("1.00000"),
            close_price=Decimal("1.00100"),
            profit=Decimal("10.00"),
            commission=Decimal("0"),
            swap=Decimal("0"),
        )
        req = TradesIngestRequest(
            account_login=prod.login,
            connector_instance_id=prod.connector_instance_id or "test",
            trades=[trade_in],
            batch_sha256="f" * 64,  # deliberadamente incorrecto
        )
        before = (await session.execute(select(func.count(Trade.id)))).scalar_one()
        with pytest.raises(SealMismatchError):
            await ingest_trades(session, prod, req)
        await session.rollback()
        after = (await session.execute(select(func.count(Trade.id)))).scalar_one()
        assert after == before, "un sello invalido no debe tocar ninguna fila"


async def test_criterion_9_lyra_phoenix_redundante() -> None:
    async with _session() as session:
        profile = await _seed_profile(session)
        if profile != "full":
            pytest.skip(
                "la correlación redundante Lyra x Phoenix solo se calibra bajo --profile full"
            )

        bots = {b.id: b.name for b in (await session.execute(select(Bot))).scalars().all()}
        rows = (
            (await session.execute(select(CorrelationMatrix).order_by(CorrelationMatrix.ts.desc())))
            .scalars()
            .all()
        )
        pair = next(
            r
            for r in rows
            if {bots.get(r.bot_a_id), bots.get(r.bot_b_id)}
            == {"Lyra Scalper EURUSD", "Phoenix Scalper SPX"}
        )
        assert pair.correlation > 0.4
        assert pair.is_redundant_pair is True


async def test_criterion_10_estige_hold_sigma_go_promote_blocked() -> None:
    async with _session() as session:
        sigma_bot = (
            await session.execute(select(Bot).where(Bot.name == "Sigma MeanRev SPX"))
        ).scalar_one()
        sigma = (
            await session.execute(
                select(PipelineCandidate).where(PipelineCandidate.bot_id == sigma_bot.id)
            )
        ).scalar_one()
        assert sigma.verdict == Verdict.GO

        estige_bot = (
            await session.execute(select(Bot).where(Bot.name == "Estige Trend GBPUSD"))
        ).scalar_one()
        estige = (
            await session.execute(
                select(PipelineCandidate).where(PipelineCandidate.bot_id == estige_bot.id)
            )
        ).scalar_one()
        assert estige.verdict == Verdict.HOLD

        with pytest.raises(HTTPException) as exc_info:
            await promote_candidate(estige.id, session)
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert "gate automatico" in detail or "gate automático" in detail
