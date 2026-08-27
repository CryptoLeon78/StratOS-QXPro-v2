import { apiFetch } from "@/api/client";

// Espejo 1:1 de HeaderSummaryResponse (core-engine/src/core/routers/header.py)
export interface HeaderSummary {
  equity_eur: string;
  pnl_day: string;
  pnl_week: string;
  pnl_month: string;
  portfolio_dd_pct: string;
  ks_level: number;
  global_semaphore: string;
  mt_connected: boolean;
  open_positions: number;
  alerts: number;
  pending_decisions: number;
  data_stale_seconds: number | null;
}

export function getHeaderSummary(): Promise<HeaderSummary> {
  return apiFetch<HeaderSummary>("/api/v1/header/summary");
}

export interface EquityCurvePoint {
  date: string;
  equity: string;
}

export type EquityRange = "30d" | "90d" | "180d" | "1y" | "all";

export function getEquityCurve(range: EquityRange): Promise<EquityCurvePoint[]> {
  return apiFetch<EquityCurvePoint[]>(`/api/v1/summary/equity-curve?range=${range}`);
}
