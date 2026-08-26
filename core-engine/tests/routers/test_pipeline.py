from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import PipelinePhase
from core.db.models.pipeline import PipelineCandidate
from tests.factories import AccountFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


async def _candidate(
    db_connection: AsyncConnection, phase: PipelinePhase = PipelinePhase.F1
) -> tuple[int, int]:
    session = await _session(db_connection)
    account = AccountFactory()
    session.add(account)
    await session.flush()
    bot = BotFactory(account_id=account.id, pipeline_phase=phase)
    session.add(bot)
    await session.flush()
    candidate = PipelineCandidate(
        bot_id=bot.id,
        current_phase=phase,
        entered_phase_at=datetime.now(UTC),
        incubation_days=0,
        oos_trades=0,
    )
    session.add(candidate)
    await session.commit()
    return candidate.id, bot.id


class TestPipelineBoard:
    async def test_lists_all_candidates(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        await _candidate(db_connection)
        response = await api_client.get("/api/v1/pipeline/board")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestCreateCandidate:
    async def test_creates_at_f1(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.commit()

        response = await api_client.post("/api/v1/pipeline/candidates", json={"bot_id": bot.id})
        assert response.status_code == 201
        assert response.json()["current_phase"] == "F1"


class TestPromoteCandidate:
    async def test_manual_promotion_f1_to_f2(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        candidate_id, _ = await _candidate(db_connection, PipelinePhase.F1)
        response = await api_client.post(f"/api/v1/pipeline/{candidate_id}/promote")
        assert response.status_code == 200
        assert response.json()["current_phase"] == "F2"

    async def test_f4_promotion_is_rejected(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        candidate_id, _ = await _candidate(db_connection, PipelinePhase.F4)
        response = await api_client.post(f"/api/v1/pipeline/{candidate_id}/promote")
        assert response.status_code == 409


class TestKillCandidate:
    async def test_archives_with_autopsy(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        candidate_id, bot_id = await _candidate(db_connection, PipelinePhase.F7)
        response = await api_client.post(
            f"/api/v1/pipeline/{candidate_id}/kill",
            json={
                "cause": "ALPHA_DECAY",
                "autopsy_text": "el edge se degrado con el cambio de regimen",
                "lesson": "vigilar page-hinkley con mas frecuencia",
            },
        )
        assert response.status_code == 200
        assert response.json()["bot_id"] == bot_id
        assert response.json()["cause"] == "ALPHA_DECAY"

    async def test_rejects_empty_autopsy(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        candidate_id, _ = await _candidate(db_connection, PipelinePhase.F7)
        response = await api_client.post(
            f"/api/v1/pipeline/{candidate_id}/kill",
            json={"cause": "ALPHA_DECAY", "autopsy_text": "  ", "lesson": "algo"},
        )
        assert response.status_code == 400


class TestCandidateGate:
    async def test_returns_the_candidate(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        candidate_id, _ = await _candidate(db_connection)
        response = await api_client.get(f"/api/v1/pipeline/{candidate_id}/gate")
        assert response.status_code == 200
