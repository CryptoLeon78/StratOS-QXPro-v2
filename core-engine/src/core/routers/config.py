"""PARTE 9.2 (nuevo en G7): `GET /api/v1/config/*` -- lectura de los
umbrales/plantillas estaticos ya sembrados en `config/thresholds.seed.json`
y usados en runtime via los dataclasses de `state_machines/types.py` y
`services/ums.py` (G3/G5). Sin logica nueva: expone lo que ya existe para
que el frontend (G7: escalera Kill-Switch en Riesgo, tabla de 6 fases en
Escalado, umbrales del gate en Pipeline, instrucciones de semaforo en
Salud/Bots) no tenga que duplicar estos numeros como constantes propias
(P11 -- cero hardcoding)."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.auth.dependencies import get_current_user
from core.services.ums import DEFAULT_UMS_PHASES
from core.state_machines.types import KillSwitchConfig, PipelineGateConfig, SemaphoreConfig

router = APIRouter(
    prefix="/api/v1/config", tags=["config"], dependencies=[Depends(get_current_user)]
)

_KS_CONFIG = KillSwitchConfig()
_GATE_CONFIG = PipelineGateConfig()
_SEMAPHORE_CONFIG = SemaphoreConfig()


class KillSwitchLadderLevel(BaseModel):
    level: int
    threshold_pct: Decimal
    instruction_text: str


class UmsPhaseDefResponse(BaseModel):
    phase: int
    name: str
    equity_min: Decimal
    equity_max: Decimal | None
    kelly_fraction: Decimal
    risk_per_trade_pct_min: Decimal | None
    risk_per_trade_pct_max: Decimal | None
    risk_note: str | None


class PipelineGateThresholds(BaseModel):
    min_trades: int
    min_days: int
    pf: float
    exp: float
    sharpe: float
    maxdd: float
    min_freq_week: float
    kill_pf: float
    marginal_band: float


class SemaphoreInstructions(BaseModel):
    verde: str
    amarillo: str
    naranja_template: str


@router.get("/killswitch-ladder", response_model=list[KillSwitchLadderLevel])
async def killswitch_ladder() -> list[KillSwitchLadderLevel]:
    return [
        KillSwitchLadderLevel(
            level=1, threshold_pct=_KS_CONFIG.l1, instruction_text=_KS_CONFIG.instruction_l1
        ),
        KillSwitchLadderLevel(
            level=2, threshold_pct=_KS_CONFIG.l2, instruction_text=_KS_CONFIG.instruction_l2
        ),
        KillSwitchLadderLevel(
            level=3, threshold_pct=_KS_CONFIG.l3, instruction_text=_KS_CONFIG.instruction_l3
        ),
        KillSwitchLadderLevel(
            level=4, threshold_pct=_KS_CONFIG.l4, instruction_text=_KS_CONFIG.instruction_l4
        ),
    ]


@router.get("/ums-phases", response_model=list[UmsPhaseDefResponse])
async def ums_phases() -> list[UmsPhaseDefResponse]:
    return [UmsPhaseDefResponse(**phase.__dict__) for phase in DEFAULT_UMS_PHASES]


@router.get("/pipeline-gate", response_model=PipelineGateThresholds)
async def pipeline_gate_thresholds() -> PipelineGateThresholds:
    return PipelineGateThresholds(
        min_trades=_GATE_CONFIG.min_trades,
        min_days=_GATE_CONFIG.min_days,
        pf=_GATE_CONFIG.pf,
        exp=_GATE_CONFIG.exp,
        sharpe=_GATE_CONFIG.sharpe,
        maxdd=_GATE_CONFIG.maxdd,
        min_freq_week=_GATE_CONFIG.min_freq_week,
        kill_pf=_GATE_CONFIG.kill_pf,
        marginal_band=_GATE_CONFIG.marginal_band,
    )


@router.get("/semaphore-instructions", response_model=SemaphoreInstructions)
async def semaphore_instructions() -> SemaphoreInstructions:
    return SemaphoreInstructions(
        verde=_SEMAPHORE_CONFIG.instruction_verde,
        amarillo=_SEMAPHORE_CONFIG.instruction_amarillo,
        naranja_template=_SEMAPHORE_CONFIG.instruction_naranja_template,
    )
