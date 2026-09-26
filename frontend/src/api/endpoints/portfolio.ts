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
  snapshot_id: number;
  source: CorrelationSource;
  created_at: string;
}

export type CorrelationSource = "MT5_BACKTEST" | "MT5_REAL";

export interface CorrelationSnapshot {
  id: number;
  source: CorrelationSource;
  status: "COMPLETED" | "WITHHELD";
  reason: string | null;
  created_at: string;
  window_start: string | null;
  window_end: string | null;
  window_days: number;
  algorithm_version: string;
  account_scope: Record<string, unknown>;
  input_sha256: string;
  pairs: CorrelationRow[];
}

export function getPortfolioCorrelations(source: CorrelationSource, windowDays?: number): Promise<CorrelationRow[]> {
  const params = new URLSearchParams({ source });
  if (windowDays) params.set("window_days", String(windowDays));
  const query = `?${params.toString()}`;
  return apiFetch<CorrelationRow[]>(`/api/v1/portfolio/correlations${query}`);
}

export function getPortfolioCorrelationSnapshot(source: CorrelationSource, windowDays?: number): Promise<CorrelationSnapshot | null> {
  const params = new URLSearchParams({ source });
  if (windowDays) params.set("window_days", String(windowDays));
  return apiFetch<CorrelationSnapshot | null>(`/api/v1/portfolio/correlations/latest?${params.toString()}`);
}

// G10: "¿Añade valor real el portfolio?" -- espejo 1:1 de
// BenchmarkComparisonResponse/MonthlyReturnPointResponse.
export interface MonthlyReturnPoint {
  date: string;
  portfolio_return: number;
  benchmark_return: number;
}

export interface BenchmarkComparison {
  n_months: number;
  cagr_portfolio: number;
  cagr_benchmark: number;
  alpha: number;
  beta: number;
  t_stat: number;
  p_value: number;
  information_ratio: number;
  batting_average: number;
  up_capture: number | null;
  down_capture: number | null;
  monthly_points: MonthlyReturnPoint[];
}

export function getPortfolioBenchmark(): Promise<BenchmarkComparison | null> {
  return apiFetch<BenchmarkComparison | null>("/api/v1/portfolio/benchmark");
}
