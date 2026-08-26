from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import NewsImpact
from core.db.models.governance import NewsEvent
from tests.factories import AccountFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


async def _seed_event_and_bot(db_connection: AsyncConnection, now: datetime) -> str:
    session = await _session(db_connection)
    account = AccountFactory()
    session.add(account)
    await session.flush()
    bot = BotFactory(account_id=account.id, market="EURUSD")
    session.add(bot)
    session.add(
        NewsEvent(
            ts=now + timedelta(hours=10),
            currency="EUR",
            impact=NewsImpact.HIGH,
            title="CPI (YoY)",
            source="ics",
            blackout_before_min=30,
            blackout_after_min=30,
        )
    )
    await session.commit()
    return bot.name


class TestNewsShield:
    async def test_lists_upcoming_events_with_affected_bots(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        now = datetime.now(UTC)
        bot_name = await _seed_event_and_bot(db_connection, now)

        response = await api_client.get("/api/v1/news/shield", params={"hours": 48})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["currency"] == "EUR"
        assert bot_name in body[0]["affected_bots"]

    async def test_excludes_events_outside_the_window(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        session.add(
            NewsEvent(
                ts=datetime.now(UTC) + timedelta(days=10),
                currency="EUR",
                impact=NewsImpact.LOW,
                title="lejano",
                source="ics",
                blackout_before_min=30,
                blackout_after_min=30,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/news/shield", params={"hours": 48})
        assert response.status_code == 200
        assert response.json() == []


class TestNewsShieldWindows:
    async def test_json_format(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        now = datetime.now(UTC)
        await _seed_event_and_bot(db_connection, now)

        response = await api_client.get(
            "/api/v1/news/shield/windows", params={"hours": 48, "format": "json"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_text_format(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        now = datetime.now(UTC)
        await _seed_event_and_bot(db_connection, now)

        response = await api_client.get(
            "/api/v1/news/shield/windows", params={"hours": 48, "format": "text"}
        )
        assert response.status_code == 200
        assert "EUR" in response.text

    async def test_csv_format(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        now = datetime.now(UTC)
        await _seed_event_and_bot(db_connection, now)

        response = await api_client.get(
            "/api/v1/news/shield/windows", params={"hours": 48, "format": "csv"}
        )
        assert response.status_code == 200
        assert response.text.startswith("start,end,currency,title")
