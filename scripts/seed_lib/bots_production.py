"""PARTE 13: 32 bots de produccion (F7/PRODUCCION, champion) + su Baseline
activa. Los 18 con nombre/magic/perfil literales del enunciado + 14 de
relleno para completar el roster y acercar los pesos de capital a la
distribucion macro 40/40/20 (foto real ~45,7/32,6/21,7) y micro 30/25/15/
10/5/5/10 -- dentro de `block_tolerance_pp=10` (thresholds.seed.json), no
ajustado al decimal (seria una ingenieria fragil sobre datos de relleno).

`underperformance_factor`: multiplicador que trades_history.py aplica a
los trades MAS RECIENTES de un bot (no al historico completo) para acercar
su P&L reciente al objetivo. NO es lo bastante fuerte por si solo para
tumbar `pf_rolling` (profit factor = ganancias/perdidas, insensible a un
simple escalado proporcional que preserva el signo) por debajo del umbral
`pf_orange` real -- verificado contra `services/semaphore_sweep.py` real:
Poseidon con factor 0.60 seguia dando pf_rolling=5,76 (sanisimo). Por eso
Poseidon/Vega llevan ADEMAS `initial_semaphore_state`/
`initial_state_days_ago`: PARTE 13 los da como HECHOS NARRATIVOS de
PARTIDA ("Poseidon... 12 dias en naranja", "Vega... amarillo 6 dias"), no
como algo que un generador puramente estadistico (sin modelo de rachas
reales) pueda re-derivar de forma fiable desde cero. El punto de PARTIDA
es dato de seed (igual que baseline/capital/magic ya lo son) -- la
TRANSICION final la sigue derivando el sweep real (derived_states.py):
Poseidon avanza AMARILLO->NARANJA porque `days_in_amarillo(20) >=
orange_days(15)` (regla real de `state_machines/semaphore.py`); Vega se
queda en AMARILLO porque sus `dias=6 < 15` y su PF/DD no fuerzan el salto
-- ninguno de los dos veredictos FINALES se escribe a mano."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from core.db.enums import BaselineSource, BotProfile, BotRole, PipelinePhase, SemaphoreState
from core.db.models.accounts import Account, Baseline, Bot
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ProductionBotSpec:
    name: str
    magic_number: int
    market: str
    timeframe: str
    profile: BotProfile
    capital_pct: Decimal
    # Baseline (source=BACKTEST, PARTE 8 -- ver Baseline en el modelo)
    pf_baseline: float
    expectancy_r_baseline: float
    sharpe_baseline: float
    max_dd_pct_baseline: Decimal
    win_rate_baseline: float
    payoff_baseline: float
    avg_trade_duration_min: float
    max_consec_losses: int
    expected_trades_30d: int
    dd_contract_pct: Decimal
    underperformance_factor: float = 1.0
    initial_semaphore_state: SemaphoreState = SemaphoreState.VERDE
    initial_state_days_ago: int = 0


# Magics de los 18 bots con dato literal en PARTE 13; el resto (relleno)
# usa un bloque de magics propio (118500+) para no colisionar.
PRODUCTION_ROSTER: tuple[ProductionBotSpec, ...] = (
    ProductionBotSpec(
        "Atlas Trend EURUSD",
        118231,
        "EURUSD",
        "H4",
        BotProfile.TREND,
        Decimal("4.50"),
        pf_baseline=1.94,
        expectancy_r_baseline=0.22,
        sharpe_baseline=1.6,
        max_dd_pct_baseline=Decimal("3.2"),
        win_rate_baseline=0.52,
        payoff_baseline=1.8,
        avg_trade_duration_min=680.0,
        max_consec_losses=4,
        expected_trades_30d=7,
        dd_contract_pct=Decimal("3.9"),
    ),
    ProductionBotSpec(
        "Helios Momentum DAX",
        118247,
        "GDAXI",
        "H1",
        BotProfile.MOMENTUM,
        Decimal("3.80"),
        pf_baseline=1.75,
        expectancy_r_baseline=0.19,
        sharpe_baseline=1.4,
        max_dd_pct_baseline=Decimal("3.6"),
        win_rate_baseline=0.48,
        payoff_baseline=1.9,
        avg_trade_duration_min=240.0,
        max_consec_losses=5,
        expected_trades_30d=12,
        dd_contract_pct=Decimal("4.2"),
    ),
    ProductionBotSpec(
        "Ariadna MeanRev SPX",
        118102,
        "SPX500",
        "H1",
        BotProfile.MEAN_REVERSION,
        Decimal("2.90"),
        pf_baseline=1.68,
        expectancy_r_baseline=0.15,
        sharpe_baseline=1.3,
        max_dd_pct_baseline=Decimal("2.8"),
        win_rate_baseline=0.61,
        payoff_baseline=1.1,
        avg_trade_duration_min=180.0,
        max_consec_losses=6,
        expected_trades_30d=18,
        dd_contract_pct=Decimal("3.4"),
    ),
    ProductionBotSpec(
        "Vega Grid GBPUSD",
        118318,
        "GBPUSD",
        "M30",
        BotProfile.GRID,
        Decimal("2.10"),
        pf_baseline=1.55,
        expectancy_r_baseline=0.12,
        sharpe_baseline=1.1,
        max_dd_pct_baseline=Decimal("4.0"),
        win_rate_baseline=0.58,
        payoff_baseline=0.95,
        avg_trade_duration_min=420.0,
        max_consec_losses=7,
        expected_trades_30d=44,
        dd_contract_pct=Decimal("4.0"),
        underperformance_factor=0.55,
        initial_semaphore_state=SemaphoreState.AMARILLO,
        initial_state_days_ago=6,  # literal PARTE 13: "amarillo 6 dias"
    ),
    ProductionBotSpec(
        "Orion Breakout XAU",
        118344,
        "XAUUSD",
        "H4",
        BotProfile.TREND,
        Decimal("3.10"),
        pf_baseline=1.80,
        expectancy_r_baseline=0.20,
        sharpe_baseline=1.5,
        max_dd_pct_baseline=Decimal("3.5"),
        win_rate_baseline=0.45,
        payoff_baseline=2.1,
        avg_trade_duration_min=560.0,
        max_consec_losses=5,
        expected_trades_30d=10,
        dd_contract_pct=Decimal("3.9"),
    ),
    ProductionBotSpec(
        "Selene MeanRev XAG",
        118360,
        "XAGUSD",
        "H1",
        BotProfile.MEAN_REVERSION,
        Decimal("2.40"),
        pf_baseline=1.62,
        expectancy_r_baseline=0.14,
        sharpe_baseline=1.2,
        max_dd_pct_baseline=Decimal("3.1"),
        win_rate_baseline=0.59,
        payoff_baseline=1.05,
        avg_trade_duration_min=200.0,
        max_consec_losses=6,
        expected_trades_30d=16,
        dd_contract_pct=Decimal("3.6"),
    ),
    ProductionBotSpec(
        "Titan Trend US30",
        118396,
        "US30",
        "H4",
        BotProfile.TREND,
        Decimal("3.30"),
        pf_baseline=1.71,
        expectancy_r_baseline=0.18,
        sharpe_baseline=1.4,
        max_dd_pct_baseline=Decimal("3.7"),
        win_rate_baseline=0.47,
        payoff_baseline=1.85,
        avg_trade_duration_min=600.0,
        max_consec_losses=5,
        expected_trades_30d=9,
        dd_contract_pct=Decimal("4.1"),
    ),
    ProductionBotSpec(
        "Nova SmartFlow EURUSD",
        118412,
        "EURUSD",
        "H1",
        BotProfile.SMART_MONEY,
        Decimal("2.60"),
        pf_baseline=1.66,
        expectancy_r_baseline=0.16,
        sharpe_baseline=1.3,
        max_dd_pct_baseline=Decimal("3.0"),
        win_rate_baseline=0.54,
        payoff_baseline=1.4,
        avg_trade_duration_min=300.0,
        max_consec_losses=5,
        expected_trades_30d=11,
        dd_contract_pct=Decimal("3.5"),
    ),
    ProductionBotSpec(
        "Cronos Swing USDJPY",
        118428,
        "USDJPY",
        "H4",
        BotProfile.TREND,
        Decimal("2.80"),
        pf_baseline=1.69,
        expectancy_r_baseline=0.17,
        sharpe_baseline=1.35,
        max_dd_pct_baseline=Decimal("3.3"),
        win_rate_baseline=0.50,
        payoff_baseline=1.7,
        avg_trade_duration_min=520.0,
        max_consec_losses=5,
        expected_trades_30d=8,
        dd_contract_pct=Decimal("3.8"),
    ),
    ProductionBotSpec(
        "Minerva AI SPX",
        118459,
        "SPX500",
        "H4",
        BotProfile.AI_ML,
        Decimal("3.20"),
        pf_baseline=1.77,
        expectancy_r_baseline=0.21,
        sharpe_baseline=1.55,
        max_dd_pct_baseline=Decimal("3.4"),
        win_rate_baseline=0.53,
        payoff_baseline=1.6,
        avg_trade_duration_min=250.0,
        max_consec_losses=4,
        expected_trades_30d=14,
        dd_contract_pct=Decimal("3.9"),
    ),
    ProductionBotSpec(
        "Boreas Trend USOIL",
        118473,
        "USOIL",
        "H4",
        BotProfile.TREND,
        Decimal("2.70"),
        pf_baseline=1.64,
        expectancy_r_baseline=0.15,
        sharpe_baseline=1.25,
        max_dd_pct_baseline=Decimal("3.8"),
        win_rate_baseline=0.46,
        payoff_baseline=1.75,
        avg_trade_duration_min=540.0,
        max_consec_losses=6,
        expected_trades_30d=9,
        dd_contract_pct=Decimal("4.3"),
    ),
    ProductionBotSpec(
        "Lyra Scalper EURUSD",
        118423,
        "EURUSD",
        "M5",
        BotProfile.SCALPING,
        Decimal("2.10"),
        pf_baseline=1.48,
        expectancy_r_baseline=0.06,
        sharpe_baseline=1.1,
        max_dd_pct_baseline=Decimal("2.2"),
        win_rate_baseline=0.87,
        payoff_baseline=0.42,
        avg_trade_duration_min=12.0,
        max_consec_losses=8,
        expected_trades_30d=58,
        dd_contract_pct=Decimal("2.6"),
    ),
    ProductionBotSpec(
        "Phoenix Scalper SPX",
        118429,
        "SPX500",
        "M5",
        BotProfile.SCALPING,
        Decimal("1.90"),
        pf_baseline=1.44,
        expectancy_r_baseline=0.05,
        sharpe_baseline=1.05,
        max_dd_pct_baseline=Decimal("2.4"),
        win_rate_baseline=0.84,
        payoff_baseline=0.44,
        avg_trade_duration_min=14.0,
        max_consec_losses=8,
        expected_trades_30d=52,
        dd_contract_pct=Decimal("2.8"),
    ),
    ProductionBotSpec(
        "Perseo Momentum NAS",
        118435,
        "NDX",
        "H1",
        BotProfile.MOMENTUM,
        Decimal("2.50"),
        pf_baseline=1.70,
        expectancy_r_baseline=0.17,
        sharpe_baseline=1.4,
        max_dd_pct_baseline=Decimal("3.6"),
        win_rate_baseline=0.47,
        payoff_baseline=1.85,
        avg_trade_duration_min=220.0,
        max_consec_losses=5,
        expected_trades_30d=13,
        dd_contract_pct=Decimal("4.0"),
    ),
    ProductionBotSpec(
        "Danae MeanRev GBPUSD",
        118441,
        "GBPUSD",
        "H1",
        BotProfile.MEAN_REVERSION,
        Decimal("2.30"),
        pf_baseline=1.60,
        expectancy_r_baseline=0.13,
        sharpe_baseline=1.2,
        max_dd_pct_baseline=Decimal("2.9"),
        win_rate_baseline=0.60,
        payoff_baseline=1.0,
        avg_trade_duration_min=190.0,
        max_consec_losses=6,
        expected_trades_30d=17,
        dd_contract_pct=Decimal("3.4"),
    ),
    ProductionBotSpec(
        "Hermes OrderFlow EURUSD",
        118447,
        "EURUSD",
        "H1",
        BotProfile.SMART_MONEY,
        Decimal("2.20"),
        pf_baseline=1.63,
        expectancy_r_baseline=0.15,
        sharpe_baseline=1.25,
        max_dd_pct_baseline=Decimal("3.1"),
        win_rate_baseline=0.55,
        payoff_baseline=1.35,
        avg_trade_duration_min=310.0,
        max_consec_losses=5,
        expected_trades_30d=10,
        dd_contract_pct=Decimal("3.6"),
    ),
    ProductionBotSpec(
        "Rhea Trend XAG",
        118452,
        "XAGUSD",
        "H4",
        BotProfile.TREND,
        Decimal("2.60"),
        pf_baseline=1.67,
        expectancy_r_baseline=0.16,
        sharpe_baseline=1.3,
        max_dd_pct_baseline=Decimal("3.4"),
        win_rate_baseline=0.48,
        payoff_baseline=1.7,
        avg_trade_duration_min=530.0,
        max_consec_losses=5,
        expected_trades_30d=8,
        dd_contract_pct=Decimal("3.9"),
    ),
    ProductionBotSpec(
        "Poseidón Trend GER40",
        118685,
        "GDAXI",
        "H1",
        BotProfile.TREND,
        Decimal("2.80"),
        pf_baseline=1.94,
        expectancy_r_baseline=0.20,
        sharpe_baseline=1.5,
        max_dd_pct_baseline=Decimal("3.3"),
        win_rate_baseline=0.49,
        payoff_baseline=1.8,
        avg_trade_duration_min=310.0,
        max_consec_losses=5,
        expected_trades_30d=11,
        dd_contract_pct=Decimal("3.9"),
        underperformance_factor=0.60,
        initial_semaphore_state=SemaphoreState.AMARILLO,
        # >orange_days(15): el sweep real la avanza a NARANJA en esta misma
        # pasada (regla `days_in_amarillo >= orange_days`,
        # state_machines/semaphore.py) -- crea tambien la Decision
        # Confirmar/Posponer/Descartar pendiente que pide el criterio 2,
        # porque la transicion ocurre DURANTE el seed, no antes.
        initial_state_days_ago=20,
    ),
)

# 14 bots de relleno (sin captura literal), pesos elegidos para acercar el
# reparto de capital a la foto macro/micro del enunciado dentro de la
# tolerancia de 10pp -- no se persigue el decimal exacto.
_FILLER_MARKETS = ("EURUSD", "GBPUSD", "XAUUSD", "US30", "SPX500", "GDAXI", "NDX", "USOIL")


def _filler_roster() -> tuple[ProductionBotSpec, ...]:
    fillers: list[ProductionBotSpec] = []
    # Nombres deliberadamente DISTINTOS de los ~18 con nombre de arriba Y de
    # los ~25 de la cantera (bots_pipeline.py: Zephyr/Boreal/Kairos/Lete/
    # Talos/Eco/Umbra/Draco/Nix/Ceres/Hera/Janus/Tetis/Electra/Ofion/
    # Cefiro/Palas/Ninfa/Sigma/Delfos/Estige/Vulcano/Helios v2/Ariadna v3) --
    # hallazgo real durante la implementacion de bots_pipeline.py: la
    # primera version de este relleno REUTILIZABA por error los nombres
    # literales de la cantera de PARTE 13, lo que habria creado bots
    # duplicados de nombre entre produccion y cantera. Perfiles/pesos
    # identicos a la version anterior (el ajuste de tolerancia ya
    # verificado sigue siendo valido, solo cambian los nombres).
    plan = [
        ("Iris AI USTEC", BotProfile.AI_ML, Decimal("3.00")),
        ("Nike SmartFlow SPX", BotProfile.SMART_MONEY, Decimal("2.00")),
        ("Eos Momentum XAG", BotProfile.MOMENTUM, Decimal("2.20")),
        ("Thalia MeanRev GER40", BotProfile.MEAN_REVERSION, Decimal("2.50")),
        ("Circe MeanRev USTEC", BotProfile.MEAN_REVERSION, Decimal("2.10")),
        ("Calisto MeanRev USOIL", BotProfile.MEAN_REVERSION, Decimal("2.30")),
        ("Baco Scalper GBPUSD", BotProfile.SCALPING, Decimal("1.80")),
        ("Pandora Momentum EURUSD", BotProfile.MOMENTUM, Decimal("2.10")),
        ("Eros AI XAG", BotProfile.AI_ML, Decimal("2.40")),
        ("Astrea MeanRev EURUSD", BotProfile.MEAN_REVERSION, Decimal("2.00")),
        ("Deimos Trend SPX", BotProfile.TREND, Decimal("2.20")),
        ("Fobos SmartFlow GBPUSD", BotProfile.SMART_MONEY, Decimal("1.90")),
        ("Nyx MeanRev USOIL", BotProfile.MEAN_REVERSION, Decimal("2.00")),
        ("Hipnos Grid US30", BotProfile.GRID, Decimal("1.70")),
    ]
    for i, (name, profile, capital_pct) in enumerate(plan):
        fillers.append(
            ProductionBotSpec(
                name,
                118500 + i,
                _FILLER_MARKETS[i % len(_FILLER_MARKETS)],
                "H1",
                profile,
                capital_pct,
                pf_baseline=1.6,
                expectancy_r_baseline=0.14,
                sharpe_baseline=1.2,
                max_dd_pct_baseline=Decimal("3.5"),
                win_rate_baseline=0.52,
                payoff_baseline=1.4,
                avg_trade_duration_min=300.0,
                max_consec_losses=5,
                expected_trades_30d=12,
                dd_contract_pct=Decimal("4.0"),
            )
        )
    return tuple(fillers)


def full_production_roster() -> tuple[ProductionBotSpec, ...]:
    return PRODUCTION_ROSTER + _filler_roster()


async def seed_production_bots(
    session: AsyncSession, account: Account, roster: tuple[ProductionBotSpec, ...], now: datetime
) -> dict[str, Bot]:
    """Devuelve {nombre: Bot} para que otros modulos (graveyard, escenarios,
    correlaciones) puedan referenciar bots por nombre sin volver a consultar."""
    bots_by_name: dict[str, Bot] = {}
    for spec in roster:
        entered_state_at = now - timedelta(days=spec.initial_state_days_ago)
        sizing_current_pct = (
            Decimal("50.00")
            if spec.initial_semaphore_state == SemaphoreState.AMARILLO
            else Decimal("100.00")
        )
        bot = Bot(
            account_id=account.id,
            magic_number=spec.magic_number,
            name=spec.name,
            market=spec.market,
            timeframe=spec.timeframe,
            profile=spec.profile,
            role=BotRole.CHAMPION,
            slot=f"{spec.profile.value.lower()}-{spec.market.lower()}",
            pipeline_phase=PipelinePhase.F7,
            semaphore_state=spec.initial_semaphore_state,
            entered_state_at=entered_state_at,
            capital_allocated_pct=spec.capital_pct,
            risk_per_trade_pct=Decimal("0.500"),
            sizing_multiplier=Decimal("1.00"),
            sizing_current_pct=sizing_current_pct,
            kelly_fraction=Decimal("0.25"),
            created_at=now,
        )
        session.add(bot)
        await session.flush()

        baseline = Baseline(
            bot_id=bot.id,
            source=BaselineSource.BACKTEST,
            profit_factor=spec.pf_baseline,
            expectancy_r=spec.expectancy_r_baseline,
            sharpe=spec.sharpe_baseline,
            max_dd_pct=spec.max_dd_pct_baseline,
            win_rate=spec.win_rate_baseline,
            payoff=spec.payoff_baseline,
            avg_trade_duration_min=spec.avg_trade_duration_min,
            max_consec_losses=spec.max_consec_losses,
            expected_trades_30d=spec.expected_trades_30d,
            dd_contract_pct=spec.dd_contract_pct,
            created_at=now,
            is_active=True,
        )
        session.add(baseline)
        await session.flush()
        bot.baseline_id = baseline.id

        bots_by_name[spec.name] = bot

    return bots_by_name
