from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis

from core.db.enums import PipelinePhase, SemaphoreState
from core.services.semaphore_sweep import SemaphoreSweepConfig, sweep_all_bots
from core.state_machines.types import SemaphoreConfig
from tests.factories import (
    AccountFactory,
    BaselineFactory,
    BotFactory,
    IngestBatchFactory,
    TradeFactory,
)

CONFIG = SemaphoreConfig()
SWEEP_CONFIG = SemaphoreSweepConfig(rolling_window_trades=20)


async def _account(db_session: object) -> object:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account


class TestSweepAllBots:
    async def test_poseidon_style_bot_demotes_to_amarillo(self, db_session: object) -> None:
        # PARTE 1/12: Poseidon Trend GER40, PF rodante 1,18 vs baseline
        # 1,94 -> AMARILLO. Reproducido aqui con datos reales (10 ganadoras
        # de 11,80 + 10 perdedoras de 10,00 -> PF exacto 1,18).
        account = await _account(db_session)
        bot = BotFactory(
            account_id=account.id,
            semaphore_state=SemaphoreState.VERDE,
            magic_number=118685,
        )
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        baseline = BaselineFactory(
            bot_id=bot.id,
            profit_factor=1.94,
            expectancy_r=0.2,
            # holgado a proposito: el objetivo de este test es la rama
            # AMARILLO (pf_rolling bajo), no el CONTRACT_BREACH del propio
            # dd_bot_pct reconstruido de la curva sintetica de trades.
            dd_contract_pct=Decimal("20.000"),
        )
        db_session.add(baseline)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot.baseline_id = baseline.id  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        now = datetime.now(UTC)
        for i in range(20):
            profit = Decimal("11.80") if i % 2 == 0 else Decimal("-10.00")
            close_time = now - timedelta(days=20 - i)
            db_session.add(  # type: ignore[attr-defined]
                TradeFactory(
                    bot_id=bot.id,
                    account_id=account.id,
                    magic_number=bot.magic_number,
                    open_time=close_time - timedelta(hours=1),
                    close_time=close_time,
                    close_price=Decimal("1.1"),
                    profit=profit,
                    commission=Decimal("0.00"),
                    swap=Decimal("0.00"),
                    ingest_batch_id=batch.id,
                )
            )
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        await sweep_all_bots(db_session, redis, CONFIG, SWEEP_CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        from core.db.models.accounts import Bot as BotModel

        refreshed = await db_session.get(BotModel, bot.id)  # type: ignore[attr-defined]
        assert refreshed.semaphore_state == SemaphoreState.AMARILLO
        await redis.aclose()

    async def test_bot_without_baseline_is_skipped(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.VERDE)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await sweep_all_bots(db_session, redis, CONFIG, SWEEP_CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        from core.db.models.accounts import Bot as BotModel

        refreshed = await db_session.get(BotModel, bot.id)  # type: ignore[attr-defined]
        assert refreshed.semaphore_state == SemaphoreState.VERDE
        await redis.aclose()

    async def test_cemetery_bot_is_skipped(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(
            account_id=account.id,
            semaphore_state=SemaphoreState.VERDE,
            pipeline_phase=PipelinePhase.CEMENTERIO,
        )
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        baseline = BaselineFactory(bot_id=bot.id, profit_factor=1.94, expectancy_r=0.2)
        db_session.add(baseline)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        bot.baseline_id = baseline.id  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await sweep_all_bots(db_session, redis, CONFIG, SWEEP_CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        from core.db.models.accounts import Bot as BotModel

        refreshed = await db_session.get(BotModel, bot.id)  # type: ignore[attr-defined]
        assert refreshed.semaphore_state == SemaphoreState.VERDE
        await redis.aclose()
