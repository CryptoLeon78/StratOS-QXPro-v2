import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/config.py (nuevo en G7) -- umbrales estaticos
// de thresholds.seed.json que ningun otro endpoint expone.
export interface KillSwitchLadderLevel {
  level: number;
  threshold_pct: string;
  instruction_text: string;
}

export function getKillSwitchLadder(): Promise<KillSwitchLadderLevel[]> {
  return apiFetch<KillSwitchLadderLevel[]>("/api/v1/config/killswitch-ladder");
}

export interface UmsPhaseDef {
  phase: number;
  name: string;
  equity_min: string;
  equity_max: string | null;
  kelly_fraction: string;
  risk_per_trade_pct_min: string | null;
  risk_per_trade_pct_max: string | null;
  risk_note: string | null;
}

export function getUmsPhasesConfig(): Promise<UmsPhaseDef[]> {
  return apiFetch<UmsPhaseDef[]>("/api/v1/config/ums-phases");
}

export interface PipelineGateThresholds {
  min_trades: number;
  min_days: number;
  pf: number;
  exp: number;
  sharpe: number;
  maxdd: number;
  min_freq_week: number;
  kill_pf: number;
  marginal_band: number;
}

export function getPipelineGateThresholds(): Promise<PipelineGateThresholds> {
  return apiFetch<PipelineGateThresholds>("/api/v1/config/pipeline-gate");
}

export interface SemaphoreInstructions {
  verde: string;
  amarillo: string;
  naranja_template: string;
}

export function getSemaphoreInstructions(): Promise<SemaphoreInstructions> {
  return apiFetch<SemaphoreInstructions>("/api/v1/config/semaphore-instructions");
}
