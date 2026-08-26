"""Enums contractuales de PARTE 5.1. Cada uno se mapea a un ENUM nativo de
Postgres via SQLAlchemy (Alembic los crea/gestiona)."""

from enum import StrEnum


class BotProfile(StrEnum):
    TREND = "TREND"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    GRID = "GRID"
    SCALPING = "SCALPING"
    SMART_MONEY = "SMART_MONEY"
    AI_ML = "AI_ML"


class BotRole(StrEnum):
    CHAMPION = "CHAMPION"
    CHALLENGER = "CHALLENGER"


class PipelinePhase(StrEnum):
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    PRODUCCION = "PRODUCCION"
    CEMENTERIO = "CEMENTERIO"


class SemaphoreState(StrEnum):
    VERDE = "VERDE"
    AMARILLO = "AMARILLO"
    NARANJA = "NARANJA"


class AlertLevel(StrEnum):
    INFO = "INFO"
    SUAVE = "SUAVE"
    CRITICA = "CRITICA"


class BaselineSource(StrEnum):
    BACKTEST = "BACKTEST"
    HISTORICO = "HISTORICO"


class Verdict(StrEnum):
    GO = "GO"
    HOLD = "HOLD"
    KILL = "KILL"


class TradeType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class ImpulseAction(StrEnum):
    PAUSE_BOT = "PAUSE_BOT"
    CLOSE_POSITION = "CLOSE_POSITION"
    INCREASE_RISK = "INCREASE_RISK"
    DECREASE_RISK = "DECREASE_RISK"
    OTHER = "OTHER"


class ImpulseStatus(StrEnum):
    PENDING = "PENDING"
    EVALUATING = "EVALUATING"
    CLOSED = "CLOSED"


class CemeteryCause(StrEnum):
    ALPHA_DECAY = "ALPHA_DECAY"
    OVERFITTING = "OVERFITTING"
    REGIME_CHANGE = "REGIME_CHANGE"
    BROKER_UNFAVORABLE = "BROKER_UNFAVORABLE"
    OUTPERFORMED_BY_CHALLENGER = "OUTPERFORMED_BY_CHALLENGER"
    COMPETITIVE_NOT_SUPERIOR = "COMPETITIVE_NOT_SUPERIOR"
    OTHER = "OTHER"


class ChecklistType(StrEnum):
    SUNDAY = "SUNDAY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class ActorType(StrEnum):
    SYSTEM = "SYSTEM"
    HUMAN = "HUMAN"


class NewsImpact(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DecisionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    POSTPONED = "POSTPONED"
    DISMISSED = "DISMISSED"
