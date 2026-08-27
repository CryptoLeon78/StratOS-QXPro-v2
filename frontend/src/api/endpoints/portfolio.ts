import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/portfolio.py.
export interface AllocationRow {
  key: string;
  target_pct: number;
  real_pct: number;
  delta_pct: number;
  bot_count: number;
}

export function getPortfolioBlocks(): Promise<AllocationRow[]> {
  return apiFetch<AllocationRow[]>("/api/v1/portfolio/blocks");
}

export function getPortfolioProfiles(): Promise<AllocationRow[]> {
  return apiFetch<AllocationRow[]>("/api/v1/portfolio/profiles");
}

export interface CorrelationRow {
  bot_a_id: number;
  bot_b_id: number;
  correlation: number;
  is_redundant_pair: boolean;
  ts: string;
}

export function getPortfolioCorrelations(windowDays?: number): Promise<CorrelationRow[]> {
  const query = windowDays ? `?window_days=${windowDays}` : "";
  return apiFetch<CorrelationRow[]>(`/api/v1/portfolio/correlations${query}`);
}
