"""PARTE 13: 9 lapidas del Graveyard, textos literales del enunciado."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from core.db.enums import BotProfile, BotRole, CemeteryCause, PipelinePhase
from core.db.models.accounts import Account, Bot
from core.db.models.pipeline import CemeteryEntry
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class GraveyardSpec:
    name: str
    magic_number: int
    market: str
    profile: BotProfile
    cause: CemeteryCause
    autopsy_text: str
    lesson: str
    retired_days_ago: int


GRAVEYARD_ROSTER: tuple[GraveyardSpec, ...] = (
    GraveyardSpec(
        "Prometeo Trend EURUSD",
        117021,
        "EURUSD",
        BotProfile.TREND,
        CemeteryCause.ALPHA_DECAY,
        "El filtro de tendencia por ADX dejo de discriminar en cuanto subio la "
        "volatilidad de 2022. El proximo trend de EURUSD debe validar el filtro "
        "de regimen en al menos dos ciclos de volatilidad distintos.",
        "Un filtro que solo se probo en un regimen no sobrevive al siguiente.",
        1200,
    ),
    GraveyardSpec(
        "Ligeia Grid EURUSD",
        117044,
        "EURUSD",
        BotProfile.GRID,
        CemeteryCause.BROKER_UNFAVORABLE,
        "El spread medio nocturno del broker se comio la expectancy (0,19R -> "
        "0,04R). Los scalpers de M5 necesitan TCA previo con el spread real por "
        "sesion antes de produccion.",
        "Un grid rentable en backtest puede no serlo con el spread real de sesion.",
        1100,
    ),
    GraveyardSpec(
        "Dedalo Momentum GER40",
        117069,
        "GDAXI",
        BotProfile.MOMENTUM,
        CemeteryCause.OUTPERFORMED_BY_CHALLENGER,
        "Helios supero los 5 criterios en la evaluacion de febrero "
        "(Sharpe x1,22, p=0,03). Rotacion limpia: mismo slot, correlacion 0,31.",
        "La rotacion darwiniana funciona: el challenger mejor gana el slot.",
        950,
    ),
    GraveyardSpec(
        "Caronte MeanRev US30",
        117088,
        "US30",
        BotProfile.MEAN_REVERSION,
        CemeteryCause.OVERFITTING,
        "WFE 0,34 en la re-validacion trimestral: el grueso del edge estaba en "
        "2021H2. Endurecer el minimo de WFE a 0,5 antes de staging.",
        "Un WFE bajo en re-validacion es la senal mas fiable de overfitting.",
        870,
    ),
    GraveyardSpec(
        "Niobe Swing USDJPY",
        117105,
        "USDJPY",
        BotProfile.TREND,
        CemeteryCause.REGIME_CHANGE,
        "La intervencion del BoJ cambio la microestructura del par: 9 perdidas "
        "consecutivas vs 5 del baseline y Page-Hinkley disparado. Salida por "
        "protocolo NARANJA->ROJO, sin discrecionalidad.",
        "El protocolo de salida por cambio de regimen no admite excepciones.",
        700,
    ),
    GraveyardSpec(
        "Egeo Breakout XAG",
        117131,
        "XAGUSD",
        BotProfile.TREND,
        CemeteryCause.ALPHA_DECAY,
        "PF forward 1,05 vs 1,9 del backtest (desviacion -45%, alarma del "
        "comparador). Muerto en incubacion: el pipeline hizo su trabajo antes "
        "de arriesgar sizing real.",
        "El gate de incubacion existe justo para casos como este.",
        520,
    ),
    GraveyardSpec(
        "Anfitrite MeanRev GBPUSD",
        117152,
        "GBPUSD",
        BotProfile.MEAN_REVERSION,
        CemeteryCause.OUTPERFORMED_BY_CHALLENGER,
        "Danae gano la rotacion darwiniana con Recovery Factor 4,1 vs 2,6 y "
        "correlacion menor con el resto del bloque concavo.",
        "Entre dos bots similares, el de menor correlacion con el bloque gana empates.",
        280,
    ),
    GraveyardSpec(
        "Morfeo AI USTEC",
        117170,
        "NDX",
        BotProfile.AI_ML,
        CemeteryCause.OVERFITTING,
        "El modelo degrado en cuanto salio de su ventana de entrenamiento "
        "(2022-2023H1). Los bots ML exigen re-entrenamiento programado y "
        "validacion walk-forward anclada, no una foto estatica.",
        "Un modelo ML sin re-entrenamiento programado tiene fecha de caducidad.",
        160,
    ),
    GraveyardSpec(
        "Tique Scalper US30",
        117198,
        "US30",
        BotProfile.SCALPING,
        CemeteryCause.COMPETITIVE_NOT_SUPERIOR,
        "Nunca fue peor que Fenix pero tampoco lo supero en 14 meses. Plaza "
        "liberada para dar hueco a candidatos con mas asimetria (regla de los "
        "6 meses aplicada tarde: apuntada para la reestructuracion anual).",
        "Ser competitivo no basta para conservar el slot -- hay que ser superior.",
        30,
    ),
)


async def seed_graveyard(
    session: AsyncSession, prod: Account, now: datetime
) -> dict[str, CemeteryEntry]:
    entries_by_name: dict[str, CemeteryEntry] = {}
    for spec in GRAVEYARD_ROSTER:
        retired_at = now - timedelta(days=spec.retired_days_ago)
        bot = Bot(
            account_id=prod.id,
            magic_number=spec.magic_number,
            name=spec.name,
            market=spec.market,
            timeframe="H4",
            profile=spec.profile,
            role=BotRole.CHALLENGER,
            slot=None,
            pipeline_phase=PipelinePhase.CEMENTERIO,
            entered_state_at=retired_at,
            capital_allocated_pct=Decimal("0"),
            risk_per_trade_pct=Decimal("0"),
            created_at=retired_at,
        )
        session.add(bot)
        await session.flush()

        entry = CemeteryEntry(
            bot_id=bot.id,
            retired_at=retired_at,
            cause=spec.cause,
            autopsy_text=spec.autopsy_text,
            lesson=spec.lesson,
        )
        session.add(entry)
        await session.flush()
        entries_by_name[spec.name] = entry

    return entries_by_name
