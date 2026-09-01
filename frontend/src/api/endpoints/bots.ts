import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/bots.py::BotResponse -- schema "maestro" del
// bot, el mas completo de todos los routers de dominio.
export interface BotRow {
  id: number;
  account_id: number;
  magic_number: number;
  name: string;
  market: string;
  timeframe: string;
  profile: string | null;
  role: "CHAMPION" | "CHALLENGER";
  origin_kind: "EXTERNAL_PRODUCTION" | "INCUBATION" | "ANALYSIS";
  account_origin: "BROKER_REAL" | "BROKER_DEMO" | "FIXTURE";
  slot: string | null;
  pipeline_phase: string;
  semaphore_state: string;
  entered_state_at: string;
  capital_allocated_pct: string | null;
  risk_per_trade_pct: string | null;
  sizing_multiplier: string;
  sizing_current_pct: string;
  kelly_fraction: string | null;
  created_at: string;
  baseline_id: number | null;
}

export function getBots(): Promise<BotRow[]> {
  return apiFetch<BotRow[]>("/api/v1/bots");
}

// Scoped variant for account/provenance-aware views. Keep getBots parameterless:
// TanStack Query invokes a queryFn with its QueryFunctionContext argument.
export function getScopedBots(accountId?: number, dataOrigin?: BotRow["account_origin"]): Promise<BotRow[]> {
  const params = new URLSearchParams();
  if (accountId !== undefined) params.set("account_id", String(accountId));
  if (dataOrigin !== undefined) params.set("data_origin", dataOrigin);
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<BotRow[]>(`/api/v1/bots${suffix}`);
}

export function getBot(botId: number): Promise<BotRow> {
  return apiFetch<BotRow>(`/api/v1/bots/${botId}`);
}

export interface SemaphoreHistoryRow {
  id: number;
  ts: string;
  from_state: string;
  to_state: string;
  trigger_metrics: Record<string, unknown>;
  instruction_text: string;
  confirmed_at: string | null;
  confirmed_by: string | null;
}

export function getBotSemaphoreHistory(botId: number): Promise<SemaphoreHistoryRow[]> {
  return apiFetch<SemaphoreHistoryRow[]>(`/api/v1/bots/${botId}/semaphore-history`);
}

// Espejo 1:1 de core/routers/bots.py::OpenPositionRow (G10, grupo g).
export interface OpenPositionRow {
  id: number;
  ticket_mt5: number;
  symbol: string;
  type: string;
  open_time: string;
  volume: string;
  open_price: string;
  sl: string | null;
  tp: string | null;
  profit: string;
}

export function getBotOpenPositions(botId: number): Promise<OpenPositionRow[]> {
  return apiFetch<OpenPositionRow[]>(`/api/v1/bots/${botId}/open-positions`);
}

// Espejo 1:1 de core/routers/bots.py::PnlCurvePoint (G10, grupo m-02a).
export interface PnlCurvePoint {
  ts: string | null;
  cumulative_pnl: string;
}

export function getBotPnlCurve(botId: number): Promise<PnlCurvePoint[]> {
  return apiFetch<PnlCurvePoint[]>(`/api/v1/bots/${botId}/pnl-curve`);
}

export function getBotRMultiples(botId: number): Promise<string[]> {
  return apiFetch<string[]>(`/api/v1/bots/${botId}/r-multiples`);
}

// Espejo 1:1 de core/routers/bots.py::BotMetricsResponse (G10, grupo m-02a).
export interface BotMetricsResponse {
  has_baseline: boolean;
  sharpe_rolling: number | null;
  pf_rolling: number | null;
  exp_rolling: number | null;
  win_rate_rolling: number | null;
  payoff_rolling: number | null;
  avg_trade_duration_rolling_min: number | null;
  loss_streak: number | null;
  loss_streak_baseline: number | null;
  dd_rolling_pct: string | null;
  sharpe_baseline: number | null;
  pf_baseline: number | null;
  exp_baseline: number | null;
  win_rate_baseline: number | null;
  payoff_baseline: number | null;
  avg_trade_duration_baseline_min: number | null;
  dd_contract_pct: string | null;
  sortino: number | null;
  calmar: number | null;
  max_dd_pct: number;
  ulcer_index: number;
  recovery_factor: number | null;
  net_pnl: string;
  trades_per_month: number;
  pct_of_total_pnl: number | null;
  correlation_vs_rest: number | null;
  pnl_bot: string;
  pnl_account: string;
}

export function getBotMetrics(botId: number): Promise<BotMetricsResponse> {
  return apiFetch<BotMetricsResponse>(`/api/v1/bots/${botId}/metrics`);
}
