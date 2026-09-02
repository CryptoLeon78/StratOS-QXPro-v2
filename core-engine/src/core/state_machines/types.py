"""Tipos compartidos por las 3 maquinas de estado de PARTE 6. Los defaults
de los `*Config` reflejan 1:1 las claves ya sembradas en
`config/thresholds.seed.json` (G0/G3-01) -- el JSON es la fuente unica
(P11), los defaults de aqui son solo para que las funciones puras sean
invocables/testeables sin cargar el fichero completo, mismo patron que las
firmas de PARTE 8 en G2."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from core.db.enums import AlertLevel


@dataclass(frozen=True)
class TransitionResult:
    """Resultado de cualquier transicion de maquina de estado (semaforo o
    kill-switch: from_state/to_state son los valores de sus enums/niveles
    como texto)."""

    changed: bool
    from_state: str
    to_state: str
    decision_type: str | None
    instruction_text: str | None
    severity: AlertLevel | None
    requires_confirmation: bool
    trigger_metrics: dict[str, Any]
    new_sizing_pct: Decimal | None = None


@dataclass(frozen=True)
class SemaphoreMetrics:
    pf_rolling: float
    pf_baseline: float
    exp_rolling: float
    exp_baseline: float
    loss_streak: int
    loss_streak_p99_baseline: int
    page_hinkley_triggered: bool
    dd_bot_pct: Decimal
    dd_contract_pct: Decimal
    pf_virtual: float | None = None
    exp_virtual: float | None = None


@dataclass(frozen=True)
class SemaphoreConfig:
    pf_warn: float = 0.75
    pf_orange: float = 0.60
    pf_recover: float = 0.90
    exp_warn: float = 0.60
    exp_recover: float = 0.80
    recovery_days: int = 10
    orange_days: int = 15
    baseline_grace_days: int = 5
    orange_virtual_trades: int = 30
    dd_contract_orange_ratio: float = 0.80
    sizing_amarillo_pct: Decimal = Decimal("50")
    sizing_verde_pct: Decimal = Decimal("100")
    instruction_verde: str = "Mantener. No tocar nada."
    instruction_amarillo: str = (
        "Reducir sizing al 50% (bajar fraction Kelly). Aumentar frecuencia de revisión."
    )
    instruction_naranja_template: str = (
        "En el EA magic {magic}: desactivar apertura de nuevas posiciones "
        "(modo paper) y dejar cerrar las existentes por sus reglas."
    )


@dataclass(frozen=True)
class KillSwitchConfig:
    l1: Decimal = Decimal("8")
    l2: Decimal = Decimal("12")
    l3: Decimal = Decimal("15")
    l4: Decimal = Decimal("20")
    hysteresis_pp: Decimal = Decimal("2")
    instruction_l1: str = "Notificar. Vigilar sin intervenir."
    instruction_l2: str = "Reducir sizing 50% en todos los bots."
    instruction_l3: str = "Cerrar todas las posiciones abiertas."
    instruction_l4: str = "Cerrar posiciones y DESACTIVAR todos los EAs."


@dataclass(frozen=True)
class PipelineGateMetrics:
    profit_factor: float
    expectancy_r: float
    sharpe: float
    max_dd_pct: float
    oos_trades: int
    incubation_days: int
    trades_per_week: float


@dataclass(frozen=True)
class PipelineGateConfig:
    min_trades: int = 30
    min_days: int = 60
    pf: float = 1.5
    exp: float = 0.15
    sharpe: float = 1.0
    maxdd: float = 20.0
    # 0,8 op/semana por decision del operador (2026-09-02, backlog A27). El barrido de las
    # 433 candidatas Forward midio que NINGUNA llega a 2/semana: las medianas por activo van
    # de 0,53 a 0,95 y la mejor de todo el universo alcanza 1,95, asi que el umbral anterior
    # dejaba atascada en F4 a cualquier candidata de este estilo de minado. La validez
    # estadistica la sostienen min_trades=30 y min_days=60, que a 0,8/semana implican unos
    # 9 meses de historia para acumular la muestra.
    min_freq_week: float = 0.8
    kill_pf: float = 1.1  # "PF <1,1" -> KILL, PARTE 6.3
    marginal_band: float = 0.10  # "1 criterio marginal <10% del umbral" -> HOLD, PARTE 6.3
    wfe_min: float = 0.5
    sizing_total_cap: Decimal = Decimal("89")
    staging_steps: tuple[int, ...] = (10, 25, 50, 100)
    staging_min_trades: int = 20


@dataclass(frozen=True)
class GateResult:
    gates_passed: int
    gates_total: int
    verdict: str  # Verdict.GO/HOLD/KILL (str para no acoplar a core.db.enums en la firma publica)
    verdict_reason: str | None
    provisional: bool


@dataclass(frozen=True)
class ChallengerMetrics:
    sharpe: float
    p_value: float
    correlation_with_block: float
    max_dd_pct: float
    expectancy_r: float


@dataclass(frozen=True)
class ChallengerConfig:
    sharpe_ratio: float = 1.22
    p_max: float = 0.05
    overstay_months: int = 6
    instruction_overstay: str = "Competitivo pero no superior — valorar retirar y liberar plaza"
    cemetery_banner: str = (
        "Un bot retirado nunca se reactiva sin re-validación completa (pipeline desde Fase 3)."
    )


@dataclass(frozen=True)
class ChallengerResult:
    passed: bool
    criteria: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ReactivationResult:
    """Resultado de cualquier intento de reactivar un bot del Cementerio --
    PARTE 6.3: "API 409 siempre; sin control en UI". `allowed` es siempre
    False por diseno (ver `evaluate_cemetery_reactivation`)."""

    allowed: bool
    reason: str
