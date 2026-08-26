"""Tipos de resultado y de entrada ligeros que PARTE 8 referencia por nombre
(`MonteCarloResult`, `AlphaBetaResult`, `WatchdogState`, `PHResult`) sin
definir campo a campo, mas los tipos de entrada de `counterfactual_impulse`/
`sustainable_withdrawal`. Dataclasses puros -- nunca `core.db.models` (regla
"sin I/O" de PARTE 8: formulas/ no depende de la capa de persistencia)."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class WatchdogState(StrEnum):
    """PARTE 8: "OK|DEAD|RUNAWAY|OUT_OF_TOLERANCE|INSUFFICIENT_DATA" (literal)."""

    OK = "OK"
    DEAD = "DEAD"
    RUNAWAY = "RUNAWAY"
    OUT_OF_TOLERANCE = "OUT_OF_TOLERANCE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class MonteCarloResult:
    """p50/p75/p95 del maximo drawdown simulado (PARTE 8: "p50/p75/p95,
    reproducible por seed"). Mismo tipo Decimal que Baseline.max_dd_pct."""

    p50: Decimal
    p75: Decimal
    p95: Decimal
    seed: int
    n_simulations: int


@dataclass(frozen=True)
class AlphaBetaResult:
    """PARTE 8: "alpha, beta, t_stat, p, n" (literal, el orden de la
    tupla de comentario). t_stat/p_value son los de alfa (PARTE 1 cita
    "t-stat del alfa 3,42")."""

    alpha: float
    beta: float
    t_stat: float
    p_value: float
    n: int


@dataclass(frozen=True)
class PHResult:
    """Resultado del detector Page-Hinkley (autopsia Niobe, cambio de
    regimen). No definido campo a campo en PARTE 8; diseno propio
    (ASSUMPTIONS G2)."""

    change_detected: bool
    statistic: float
    change_point: int | None


@dataclass(frozen=True)
class TradeLike:
    """Entrada minima de `counterfactual_impulse`: no es `core.db.models.Trade`
    (formulas/ no depende de la capa de persistencia) -- el caller (G5)
    proyecta las columnas que necesita."""

    profit: Decimal
    commission: Decimal
    swap: Decimal


@dataclass(frozen=True)
class ImpulseSnapshot:
    """Estado del bot en el momento del impulso, necesario para simular el
    "que habria pasado si": sizing vigente en ese instante."""

    sizing_multiplier: Decimal


@dataclass(frozen=True)
class WithdrawalConfig:
    """Parametros de `sustainable_withdrawal` que en produccion vienen de
    `SystemConfig` (P11: la formula no los hardcodea, el caller los inyecta)."""

    safety_margin: Decimal
    max_dd_gate_pct: Decimal
