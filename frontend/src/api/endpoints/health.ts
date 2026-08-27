import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/health.py::HealthRow.
export interface HealthRow {
  bot_id: number;
  magic_number: number;
  name: string;
  profile: string;
  pipeline_phase: string;
  semaphore_state: string;
  days_in_state: number;
  pf_rolling: number;
  pf_baseline: number;
  exp_rolling: number;
  exp_baseline: number;
  loss_streak: number;
  dd_bot_pct: string;
  dd_contract_pct: string;
  page_hinkley_triggered: boolean;
  win_rate_drift: number;
  payoff: number | null;
  avg_trade_duration_min: number | null;
  sharpe_rolling: number;
}

export function getHealthBots(): Promise<HealthRow[]> {
  return apiFetch<HealthRow[]>("/api/v1/health/bots");
}
