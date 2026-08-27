import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/risk.py.
export interface TailRiskResponse {
  var95_daily: number;
  var99_daily: number;
  cvar95_daily: number;
  cvar99_daily: number;
  var99_monthly: number;
  cvar99_monthly: number;
  cvar99_annual: number;
  breached: boolean;
  verdict: string;
}

export function getTailRisk(): Promise<TailRiskResponse | null> {
  return apiFetch<TailRiskResponse | null>("/api/v1/risk/tail");
}

export interface ExposureRow {
  symbol: string;
  net_volume: string;
  gross_volume: string;
  pnl: string;
}

export function getExposure(): Promise<ExposureRow[]> {
  return apiFetch<ExposureRow[]>("/api/v1/risk/exposure");
}

// dd_p50/p75/p95: percentiles de drawdown de las 300 simulaciones. Sin
// "Historico"/fecha de contrato (no estan en el schema, docs/backlog.md).
export interface MonteCarloResponse {
  bot_id: number;
  ts: string;
  n_simulations: number;
  dd_p50: string;
  dd_p75: string;
  dd_p95: string;
  dd_contract_pct: string;
  seed: number;
}

export function getMonteCarlo(botId: number): Promise<MonteCarloResponse | null> {
  return apiFetch<MonteCarloResponse | null>(`/api/v1/risk/montecarlo?bot_id=${botId}`);
}
