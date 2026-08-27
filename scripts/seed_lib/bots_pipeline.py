"""PARTE 13: cantera (~25 candidatos, F1-F6). F1-F3 = zona PAPER -> cuenta
DEMO "Quarry"; F4-F6 = zona CAPITAL REAL -> cuenta REAL "Prod" (misma
distincion que el kanban de Pipeline, G7). Solo se siembran las metricas
crudas (profit_factor/expectancy_r/sharpe/max_dd_pct/oos_trades/
incubation_days/trades_per_week) -- `verdict`/`gates_passed`/`gates_total`
NUNCA se escriben a mano, los deriva el gate real en derived_states.py
(commit posterior), igual que el resto de estados del seed."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from core.db.enums import BotProfile, BotRole, PipelinePhase
from core.db.models.accounts import Account, Bot
from core.db.models.pipeline import PipelineCandidate
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PipelineBotSpec:
    name: str
    magic_number: int
    market: str
    profile: BotProfile
    phase: PipelinePhase
    incubation_days: int
    oos_trades: int
    profit_factor: float | None = None
    expectancy_r: float | None = None
    sharpe: float | None = None
    max_dd_pct: Decimal | None = None
    wfe: float | None = None
    trades_per_week: float | None = None


# F1-F3: metricas modestas, muestra insuficiente (provisional=True por
# defecto, oos_trades<30) -- son candidatos tempranos, no se espera que
# pasen el gate todavia. F4-F6: metricas literales de PARTE 13 donde el
# enunciado las da (Sigma MR, Estige, Palas); el resto, valores plausibles
# de un candidato "a mitad de camino".
PIPELINE_ROSTER: tuple[PipelineBotSpec, ...] = (
    # F1 -- ideacion y prototipado (6)
    PipelineBotSpec(
        "Zephyr Trend AUDUSD", 119001, "AUDUSD", BotProfile.TREND, PipelinePhase.F1, 18, 0
    ),
    PipelineBotSpec(
        "Boreal MeanRev GER40", 119002, "GDAXI", BotProfile.MEAN_REVERSION, PipelinePhase.F1, 13, 0
    ),
    PipelineBotSpec(
        "Kairos Momentum XAG", 119003, "XAGUSD", BotProfile.MOMENTUM, PipelinePhase.F1, 11, 0
    ),
    PipelineBotSpec("Lete Grid USDJPY", 119004, "USDJPY", BotProfile.GRID, PipelinePhase.F1, 9, 0),
    PipelineBotSpec("Talos AI US30", 119005, "US30", BotProfile.AI_ML, PipelinePhase.F1, 6, 0),
    PipelineBotSpec(
        "Eco SmartFlow SPX", 119006, "SPX500", BotProfile.SMART_MONEY, PipelinePhase.F1, 3, 0
    ),
    # F2 -- filtrado de robustez (5)
    PipelineBotSpec(
        "Umbra MeanRev USTEC", 119011, "NDX", BotProfile.MEAN_REVERSION, PipelinePhase.F2, 27, 0
    ),
    PipelineBotSpec(
        "Draco Trend USOIL", 119012, "USOIL", BotProfile.TREND, PipelinePhase.F2, 21, 0
    ),
    PipelineBotSpec(
        "Nix Scalper GBPUSD", 119013, "GBPUSD", BotProfile.SCALPING, PipelinePhase.F2, 16, 0
    ),
    PipelineBotSpec(
        "Ceres Momentum EURUSD", 119014, "EURUSD", BotProfile.MOMENTUM, PipelinePhase.F2, 12, 0
    ),
    PipelineBotSpec("Hera AI XAG", 119015, "XAGUSD", BotProfile.AI_ML, PipelinePhase.F2, 9, 0),
    # F3 -- validacion estadistica (4)
    PipelineBotSpec(
        "Janus MeanRev EURUSD",
        119021,
        "EURUSD",
        BotProfile.MEAN_REVERSION,
        PipelinePhase.F3,
        38,
        0,
        wfe=0.42,
    ),
    PipelineBotSpec(
        "Tetis Trend SPX", 119022, "SPX500", BotProfile.TREND, PipelinePhase.F3, 31, 0, wfe=0.55
    ),
    PipelineBotSpec(
        "Electra SmartFlow GBPUSD",
        119023,
        "GBPUSD",
        BotProfile.SMART_MONEY,
        PipelinePhase.F3,
        24,
        0,
        wfe=0.48,
    ),
    PipelineBotSpec(
        "Ofion Momentum USOIL",
        119024,
        "USOIL",
        BotProfile.MOMENTUM,
        PipelinePhase.F3,
        17,
        0,
        wfe=0.51,
    ),
    # F4 -- forward testing (3), zona CAPITAL REAL
    PipelineBotSpec(
        "Cefiro MeanRev XAU",
        119031,
        "XAUUSD",
        BotProfile.MEAN_REVERSION,
        PipelinePhase.F4,
        52,
        19,
        profit_factor=1.7,
        expectancy_r=0.16,
        sharpe=1.1,
        max_dd_pct=Decimal("4.5"),
        wfe=0.57,
        trades_per_week=2.6,
    ),
    # Palas: "alerta frecuencia <2/sem" -- literal del enunciado. Solo
    # trades_per_week falla (el resto pasa de sobra) para que el gate real
    # derive exactamente HOLD por ese unico criterio, no KILL por acumular
    # 2+ fallos (verificado contra evaluate_pipeline_gate real).
    PipelineBotSpec(
        "Palas Trend USTEC",
        119032,
        "NDX",
        BotProfile.TREND,
        PipelinePhase.F4,
        65,
        35,
        profit_factor=1.8,
        expectancy_r=0.18,
        sharpe=1.3,
        max_dd_pct=Decimal("3.9"),
        wfe=0.61,
        trades_per_week=1.4,
    ),
    PipelineBotSpec(
        "Ninfa Grid EURUSD",
        119033,
        "EURUSD",
        BotProfile.GRID,
        PipelinePhase.F4,
        30,
        141,
        profit_factor=1.6,
        expectancy_r=0.12,
        sharpe=1.05,
        max_dd_pct=Decimal("4.8"),
        wfe=0.53,
        trades_per_week=32.9,
    ),
    # F5 -- incubacion OOS (4), zona CAPITAL REAL
    # Sigma MR SPX: GO literal (PF 2.6, 51 trades, 95 dias).
    PipelineBotSpec(
        "Sigma MeanRev SPX",
        119041,
        "SPX500",
        BotProfile.MEAN_REVERSION,
        PipelinePhase.F5,
        95,
        51,
        profit_factor=2.6,
        expectancy_r=0.39,
        sharpe=2.1,
        max_dd_pct=Decimal("1.9"),
        wfe=0.87,
        trades_per_week=3.7,
    ),
    PipelineBotSpec(
        "Delfos Momentum XAU",
        119042,
        "XAUUSD",
        BotProfile.MOMENTUM,
        PipelinePhase.F5,
        64,
        18,
        profit_factor=1.75,
        expectancy_r=0.18,
        sharpe=1.4,
        max_dd_pct=Decimal("3.6"),
        wfe=0.70,
        trades_per_week=2.0,
    ),
    # Estige: PROVISIONAL, PF 32.75 con 9 trades (muestra insuficiente) ->
    # HOLD. Solo oos_trades falla (incubation/frequency pasan de sobra)
    # para que el gate real derive HOLD por muestra insuficiente, no KILL
    # por acumular 2+ fallos (verificado contra evaluate_pipeline_gate real).
    PipelineBotSpec(
        "Estige Trend GBPUSD",
        119043,
        "GBPUSD",
        BotProfile.TREND,
        PipelinePhase.F5,
        65,
        9,
        profit_factor=32.75,
        expectancy_r=1.8,
        sharpe=4.2,
        max_dd_pct=Decimal("0.8"),
        wfe=0.91,
        trades_per_week=2.5,
    ),
    PipelineBotSpec(
        "Vulcano Momentum US30",
        119044,
        "US30",
        BotProfile.MOMENTUM,
        PipelinePhase.F5,
        112,
        26,
        profit_factor=1.65,
        expectancy_r=0.15,
        sharpe=1.2,
        max_dd_pct=Decimal("4.1"),
        wfe=0.62,
        trades_per_week=1.6,
    ),
    # F6 -- staging (2), zona CAPITAL REAL. Helios v2: "HOLD/OVERSTAY >6
    # meses" literal -- HOLD via un unico fallo marginal de frecuencia
    # (todo lo demas pasa de sobra, verificado contra el gate real);
    # OVERSTAY es un concepto distinto (challenger >6 meses en staging,
    # PARTE 6.3) representado cronologicamente aqui (entered_phase_at
    # antiguo) -- el Decision module="challenger" que lo marca OVERSTAY en
    # el frontend (ASSUMPTIONS G6-01) lo crea scenarios.py.
    PipelineBotSpec(
        "Helios Trend v2",
        119051,
        "GDAXI",
        BotProfile.TREND,
        PipelinePhase.F6,
        198,
        100,
        profit_factor=1.9,
        expectancy_r=0.22,
        sharpe=1.6,
        max_dd_pct=Decimal("3.0"),
        wfe=0.78,
        trades_per_week=1.9,
    ),
    PipelineBotSpec(
        "Ariadna MeanRev v3",
        119052,
        "SPX500",
        BotProfile.MEAN_REVERSION,
        PipelinePhase.F6,
        45,
        25,
        profit_factor=1.72,
        expectancy_r=0.17,
        sharpe=1.35,
        max_dd_pct=Decimal("3.3"),
        wfe=0.65,
        trades_per_week=2.4,
    ),
)

_PAPER_PHASES = {PipelinePhase.F1, PipelinePhase.F2, PipelinePhase.F3}
_OVERSTAY_THRESHOLD_DAYS = 198  # >6 meses (challenger_overstay_months=6, thresholds.seed.json)


async def seed_pipeline_bots(
    session: AsyncSession, prod: Account, quarry: Account, now: datetime
) -> dict[str, PipelineCandidate]:
    candidates_by_name: dict[str, PipelineCandidate] = {}
    for spec in PIPELINE_ROSTER:
        account = quarry if spec.phase in _PAPER_PHASES else prod
        entered_phase_at = now - timedelta(days=min(spec.incubation_days, _OVERSTAY_THRESHOLD_DAYS))

        bot = Bot(
            account_id=account.id,
            magic_number=spec.magic_number,
            name=spec.name,
            market=spec.market,
            timeframe="H1",
            profile=spec.profile,
            role=BotRole.CHALLENGER,
            slot=None,
            pipeline_phase=spec.phase,
            entered_state_at=entered_phase_at,
            capital_allocated_pct=Decimal("0"),
            risk_per_trade_pct=Decimal("0.300"),
            sizing_multiplier=Decimal("1.00"),
            sizing_current_pct=Decimal("10.00") if spec.phase == PipelinePhase.F6 else Decimal("0"),
            kelly_fraction=None,
            created_at=entered_phase_at,
        )
        session.add(bot)
        await session.flush()

        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=spec.phase,
            entered_phase_at=entered_phase_at,
            incubation_days=spec.incubation_days,
            oos_trades=spec.oos_trades,
            profit_factor=spec.profit_factor,
            expectancy_r=spec.expectancy_r,
            sharpe=spec.sharpe,
            max_dd_pct=spec.max_dd_pct,
            wfe=spec.wfe,
            trades_per_week=spec.trades_per_week,
        )
        session.add(candidate)
        await session.flush()
        candidates_by_name[spec.name] = candidate

    return candidates_by_name
