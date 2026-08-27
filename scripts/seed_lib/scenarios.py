"""PARTE 13, linea "Escenarios": posicion sin SL · 3 trades huerfanos ·
bot muerto (0/12) · bot desbocado (3,4x) · 3 impulsos cerrados + 1
pendiente · noticias HIGH 48h. `crash_21`/`--inject-audit-error`/las
decisiones pendientes (Poseidon->PAPER, Sigma MR->F6) NO viven aqui:
son resultado de invocar los sweeps REALES sobre datos ya sembrados
(derived_states.py, commit siguiente) o de un test dedicado
(test_g8_acceptance_criteria.py) -- "estados derivados, no forzados"
(mismo principio que trades_history.py/bots_pipeline.py).

Watchdog (muerto/desbocado) opera SOBRE la lista de `GeneratedTrade` en
memoria, ANTES del insert -- si mutara filas ya insertadas (delete/insert
tras equity_curve.py) descuadraria la reconciliacion contable (criterio 6),
porque `EquitySnapshot.balance` ya habria sido calculado sobre el set de
trades ANTERIOR a la mutacion. huerfanos/bot-desbocado sintetico se
insertan con `profit=Decimal("0.00")` (el watchdog solo cuenta FILAS,
`func.count(Trade.id)`, nunca profit) -- asi no rompen la reconciliacion
aunque se inserten DESPUES de equity_curve.py."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from core.db.enums import ImpulseAction, ImpulseStatus, NewsImpact, TradeType
from core.db.models.accounts import Account, Bot
from core.db.models.decisions import ImpulseLog
from core.db.models.governance import NewsEvent
from core.db.models.market import IngestBatch, Trade
from core.ingest.schemas import PositionIn, PositionsIngestRequest
from core.ingest.services.positions import ingest_positions
from ingest_seal.sealing import compute_batch_sha256
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from seed_lib.bots_production import ProductionBotSpec
from seed_lib.trades_history import GeneratedTrade

# PARTE 13: "bot muerto (0/12)" / "bot desbocado (3,4x)" -- ninguno de los
# 18 bots con dato literal encaja (todos con expected_trades_30d propio,
# ver bots_production.py); se eligen 2 de los 14 de relleno, que SI
# comparten expected_trades_30d=12 con el "0/12" literal.
DEAD_BOT_NAME = "Hipnos Grid US30"
RUNAWAY_BOT_NAME = "Baco Scalper GBPUSD"
RUNAWAY_FACTOR = 3.4  # literal PARTE 13
RUNAWAY_EXPECTED_TRADES_30D = 12  # bots_production.py::_filler_roster, comun a los 14 de relleno

# mismo valor que services/watchdog.py::_WATCHDOG_WINDOW_DAYS/
# WatchdogServiceConfig.tolerance (no importados de alli para no acoplar
# scripts/ a un detalle interno de core-engine; duplicado documentado, ver
# ASSUMPTIONS G8).
_WATCHDOG_WINDOW_DAYS = 30
_WATCHDOG_TOLERANCE = 0.25

_ORPHAN_MAGIC_START = 199001  # fuera de TODOS los rangos de magic ya usados (118xxx/119xxx/117xxx)
_ORPHAN_TICKET_START = 3_900_001  # fuera del rango de trades_history.py (3.000.001+)
_MISSING_SL_TICKET = 3_950_001

# PARTE 13: "3 impulsos cerrados (418e, 236e, 0,80e) + 1 pendiente". Los
# importes exactos NO se persiguen (avoided_cost_eur lo deriva la formula
# REAL, counterfactual_impulse(), sobre los trades reales de los 7 dias
# siguientes -- forzarlo a mano violaria "estados derivados, no forzados").
# Se documenta la aproximacion en ASSUMPTIONS G8, mismo precedente que
# trades/DD/lotes.


def apply_watchdog_scenarios(
    trades: list[GeneratedTrade],
    bots_by_name: dict[str, Bot],
    now: datetime,
) -> list[GeneratedTrade]:
    """Filtra los trades ORGANICOS de los ultimos 30 dias del bot "muerto"
    (a 0) y del bot "desbocado" (a 0, para re-generarlos deterministicamente
    a continuacion) -- devuelve una lista NUEVA, no muta la de entrada."""
    window_start = now - timedelta(days=_WATCHDOG_WINDOW_DAYS)
    dead_id = bots_by_name[DEAD_BOT_NAME].id
    runaway_id = bots_by_name[RUNAWAY_BOT_NAME].id

    kept = [
        t for t in trades if not (t.bot_id in (dead_id, runaway_id) and t.open_time >= window_start)
    ]

    runaway_bot = bots_by_name[RUNAWAY_BOT_NAME]
    target_count = round(RUNAWAY_FACTOR * RUNAWAY_EXPECTED_TRADES_30D)
    window_days = [window_start.date() + timedelta(days=i) for i in range(_WATCHDOG_WINDOW_DAYS)]
    synthetic: list[GeneratedTrade] = []
    for i in range(target_count):
        day = window_days[i % len(window_days)]
        open_dt = datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(
            minutes=480 + (i * 7) % 540
        )
        synthetic.append(
            GeneratedTrade(
                bot_id=runaway_id,
                magic_number=runaway_bot.magic_number,
                symbol=runaway_bot.market,
                trade_type=TradeType.BUY if i % 2 == 0 else TradeType.SELL,
                open_time=open_dt,
                close_time=open_dt + timedelta(minutes=5),
                profit=Decimal("0.00"),
            )
        )
    return kept + synthetic


def normalize_recent_frequency(
    trades: list[GeneratedTrade],
    roster: tuple[ProductionBotSpec, ...],
    bots_by_name: dict[str, Bot],
    exempt_bot_names: set[str],
    now: datetime,
) -> list[GeneratedTrade]:
    """PARTE 1: "Atlas espera ~7 trades/mes y lleva 6; Lyra espera 58 y
    lleva 59; los 32 en verde tecnico" -- ademas de los 2 bots citados por
    nombre, el enunciado deja claro que TODOS los bots de produccion (salvo
    los deliberadamente forzados a muerto/desbocado) deben quedar OK en el
    watchdog real.

    Hallazgo real (verificado con `services/watchdog.py::evaluate_all_bots`
    contra el seed ya insertado): `frequency_scale` de trades_history.py
    escala la frecuencia de TODOS los bots a la baja para que el TOTAL de
    5+ anos se acerque al objetivo agregado de PARTE 13 (15.486) -- eso deja
    el recuento de la ventana de 30 dias del watchdog muy por debajo del
    `expected_trades_30d` propio de cada bot (ej. Lyra: 30 observados vs 58
    esperados, fuera de la tolerancia real del 25%). Este ajuste anade
    trades sinteticos de `profit=0.00` (mismo mecanismo que el bot
    desbocado) SOLO en la ventana de 30 dias, SOLO cuando el recuento ya
    generado queda por debajo del limite de tolerancia -- nunca resta, y no
    toca el resto de la historia ni el P&L."""
    window_start = now - timedelta(days=_WATCHDOG_WINDOW_DAYS)
    counts: dict[int, int] = defaultdict(int)
    for t in trades:
        if t.open_time >= window_start:
            counts[t.bot_id] += 1

    extra: list[GeneratedTrade] = []
    for i, spec in enumerate(roster):
        if spec.name in exempt_bot_names or spec.expected_trades_30d <= 0:
            continue
        bot = bots_by_name[spec.name]
        low_bound = spec.expected_trades_30d * (1 - _WATCHDOG_TOLERANCE)
        observed = counts.get(bot.id, 0)
        if observed >= low_bound:
            continue
        # Rellena hasta expected_trades_30d (no solo el borde de
        # low_bound): un margen mayor tolera la varianza de Poisson y el
        # desplazamiento natural de la ventana entre la generacion y una
        # re-evaluacion posterior (verificado: con el borde apenas
        # superado, un perfil `ci` de historia corta volvia a caer en
        # OUT_OF_TOLERANCE en varios bots, incl. Atlas -- ver ASSUMPTIONS G8).
        needed = spec.expected_trades_30d - observed
        for j in range(needed):
            day = window_start.date() + timedelta(days=(i * 5 + j * 3) % _WATCHDOG_WINDOW_DAYS)
            open_dt = datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(
                minutes=500 + (j * 11) % 400
            )
            extra.append(
                GeneratedTrade(
                    bot_id=bot.id,
                    magic_number=spec.magic_number,
                    symbol=spec.market,
                    trade_type=TradeType.BUY if j % 2 == 0 else TradeType.SELL,
                    open_time=open_dt,
                    close_time=open_dt + timedelta(minutes=5),
                    profit=Decimal("0.00"),
                )
            )
    return trades + extra


async def insert_orphan_trades(
    session: AsyncSession, account: Account, now: datetime, count: int = 3
) -> int:
    """3 trades con `bot_id=NULL` (magic_number desconocido, fuera de todo
    roster sembrado) -- PARTE 13: "3 trades huerfanos". `profit=0.00`: no
    afecta a la reconciliacion contable (criterio 6) aunque se inserten
    despues de equity_curve.py."""
    batch_ts = now - timedelta(hours=2)
    payload = [
        {"ticket_mt5": _ORPHAN_TICKET_START + i, "magic_number": _ORPHAN_MAGIC_START + i}
        for i in range(count)
    ]
    result = await session.execute(
        insert(IngestBatch)
        .values(
            ts=batch_ts,
            connector_instance_id=account.connector_instance_id or "seed-generator",
            account_id=account.id,
            batch_type="trades",
            records=count,
            sha256=compute_batch_sha256(account.login, "trades", payload),
            server_ts=batch_ts,
        )
        .returning(IngestBatch.id)
    )
    batch_id = result.scalar_one()

    rows = [
        {
            "bot_id": None,
            "account_id": account.id,
            "magic_number": _ORPHAN_MAGIC_START + i,
            "ticket_mt5": _ORPHAN_TICKET_START + i,
            "symbol": "EURUSD",
            "open_time": batch_ts,
            "close_time": batch_ts + timedelta(minutes=30),
            "type": TradeType.BUY,
            "volume": Decimal("0.10"),
            "open_price": Decimal("1.00000"),
            "close_price": Decimal("1.00000"),
            "sl": Decimal("0.99000"),
            "tp": Decimal("1.01000"),
            "profit": Decimal("0.00"),
            "commission": Decimal("0"),
            "swap": Decimal("0"),
            "r_multiple": None,
            "ingest_batch_id": batch_id,
            "ingested_at": now,
        }
        for i in range(count)
    ]
    await session.execute(insert(Trade), rows)
    return count


async def apply_missing_sl_scenario(
    session: AsyncSession, account: Account, bot: Bot, now: datetime
) -> None:
    """PARTE 13: "posicion sin SL (CRITICA P5)". Reutiliza el pathway REAL
    de ingesta (`core.ingest.services.positions.ingest_positions`) en vez
    de escribir el Trade/Alert a mano -- el mismo codigo que P5 verifica en
    produccion es el que crea el escenario, incl. el sello SHA-256 real."""
    position = PositionIn(
        ticket_mt5=_MISSING_SL_TICKET,
        symbol=bot.market,
        magic_number=bot.magic_number,
        type=TradeType.BUY,
        volume=Decimal("0.10"),
        open_time=now - timedelta(hours=3),
        open_price=Decimal("1.00000"),
        sl=None,
        tp=None,
        profit=Decimal("0.00"),
    )
    req = PositionsIngestRequest(
        account_login=account.login,
        connector_instance_id=account.connector_instance_id or "seed-generator",
        ts=now,
        positions=[position],
        batch_sha256="0" * 64,
    )
    payload = [req.model_dump(mode="json", exclude={"batch_sha256"})]
    req.batch_sha256 = compute_batch_sha256(account.login, "positions", payload)
    await ingest_positions(session, account, req)


@dataclass(frozen=True)
class ImpulseSpec:
    days_ago: float
    description: str
    desired_action: ImpulseAction


# services/impulses.py::ImpulseServiceConfig.eval_days=7 -- los 3 primeros
# (>7 dias) quedaran CLOSED cuando derived_states.py corra
# evaluate_pending_impulses(); el ultimo (<7 dias) se queda PENDING.
IMPULSE_SPECS: tuple[ImpulseSpec, ...] = (
    ImpulseSpec(45, "Impulso de pausar tras 2 perdidas seguidas.", ImpulseAction.PAUSE_BOT),
    ImpulseSpec(30, "Impulso de pausar por una vela en contra grande.", ImpulseAction.PAUSE_BOT),
    ImpulseSpec(15, "Impulso de pausar por una racha lateral.", ImpulseAction.PAUSE_BOT),
    ImpulseSpec(2, "Impulso de pausar tras una noticia inesperada.", ImpulseAction.PAUSE_BOT),
)


async def seed_impulses(session: AsyncSession, bots_by_name: dict[str, Bot], now: datetime) -> int:
    """PARTE 13: "3 impulsos cerrados + 1 pendiente". Solo se siembra el
    PENDING crudo (ts/bot/accion) -- `avoided_cost_eur`/status=CLOSED los
    deriva `services/impulses.py::evaluate_pending_impulses` (REAL, sobre
    los trades reales de los 7 dias siguientes al impulso) en
    derived_states.py, nunca a mano aqui."""
    target_bots = [
        bots_by_name["Atlas Trend EURUSD"],
        bots_by_name["Helios Momentum DAX"],
        bots_by_name["Ariadna MeanRev SPX"],
        bots_by_name["Titan Trend US30"],
    ]
    for spec, bot in zip(IMPULSE_SPECS, target_bots, strict=True):
        session.add(
            ImpulseLog(
                ts=now - timedelta(days=spec.days_ago),
                bot_id=bot.id,
                description=spec.description,
                desired_action=spec.desired_action,
                executed=False,
                status=ImpulseStatus.PENDING,
            )
        )
    await session.flush()
    return len(IMPULSE_SPECS)


@dataclass(frozen=True)
class NewsSpec:
    hours_ahead: float
    currency: str
    title: str
    source: str


NEWS_SPECS: tuple[NewsSpec, ...] = (
    NewsSpec(18, "EUR", "IFO Business Climate", "IFO Institute"),
    NewsSpec(36, "USD", "Durable Goods Orders", "US Census Bureau"),
)


async def seed_news_events(session: AsyncSession, now: datetime) -> int:
    """PARTE 13: "noticias HIGH 48h (IFO EUR, Durable Goods USD)". `ts`
    relativo a `now` (el propio momento del seed) -- `/news/shield` solo
    lista eventos con `ts` entre ahora y ahora+N horas (`routers/news.py`),
    una fecha fija de calendario quedaria fuera de ventana en cuanto pase
    el tiempo real."""
    for spec in NEWS_SPECS:
        session.add(
            NewsEvent(
                ts=now + timedelta(hours=spec.hours_ahead),
                currency=spec.currency,
                impact=NewsImpact.HIGH,
                title=spec.title,
                source=spec.source,
            )
        )
    await session.flush()
    return len(NEWS_SPECS)
