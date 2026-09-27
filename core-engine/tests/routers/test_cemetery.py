from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import ActorType, CemeteryCause, PipelinePhase
from core.db.models.pipeline import CemeteryEntry, PipelineCandidate, PipelinePhaseTransition
from tests.factories import AccountFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestListCemetery:
    async def test_lists_entries(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        session.add(
            CemeteryEntry(
                bot_id=bot.id,
                retired_at=datetime.now(UTC),
                cause=CemeteryCause.ALPHA_DECAY,
                autopsy_text="a",
                lesson="b",
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/cemetery")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["entered_pipeline_at"] is None

    async def test_entered_pipeline_at_reads_the_admission_transition(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        """docs/adr/0006: PipelinePhaseTransition (append-only desde G11) SI conserva la
        fecha real de alta a F1 -- from_phase IS NULL marca esa transicion, unica por
        candidato porque solo se escribe una vez en create_candidate."""
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        entered_at = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=PipelinePhase.F7,
            entered_phase_at=datetime.now(UTC),
            incubation_days=0,
            oos_trades=0,
        )
        session.add(candidate)
        await session.flush()
        session.add(
            PipelinePhaseTransition(
                candidate_id=candidate.id,
                from_phase=None,
                to_phase=PipelinePhase.F1,
                actor=ActorType.HUMAN,
                reason="CANDIDATE_CREATED",
                occurred_at=entered_at,
            )
        )
        session.add(
            CemeteryEntry(
                bot_id=bot.id,
                retired_at=datetime.now(UTC),
                cause=CemeteryCause.ALPHA_DECAY,
                autopsy_text="a",
                lesson="b",
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/cemetery")

        assert response.status_code == 200
        [entry] = response.json()
        assert entry["entered_pipeline_at"] == entered_at.isoformat().replace("+00:00", "Z")

    async def test_entered_pipeline_at_is_absent_without_a_candidate(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        """Un bot sembrado directamente en produccion (nunca paso por F1-F7) no tiene
        PipelineCandidate -- se declara ausencia, nunca se sustituye por Bot.created_at."""
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        session.add(
            CemeteryEntry(
                bot_id=bot.id,
                retired_at=datetime.now(UTC),
                cause=CemeteryCause.ALPHA_DECAY,
                autopsy_text="a",
                lesson="b",
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/cemetery")

        assert response.status_code == 200
        [entry] = response.json()
        assert entry["entered_pipeline_at"] is None


class TestReactivate:
    async def test_always_returns_409(self, api_client: AsyncClient) -> None:
        """Criterio de aceptacion PARTE 16 #4 ("Cementerio: 409 + sin
        control UI + banner 'pipeline desde Fase 3'") -- ver indice en
        tests/e2e/test_g5_exit_criteria.py."""
        response = await api_client.post("/api/v1/cemetery/1/reactivate")
        assert response.status_code == 409
        assert "Fase 3" in response.json()["detail"]
