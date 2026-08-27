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
  profile: string;
  role: "CHAMPION" | "CHALLENGER";
  slot: string | null;
  pipeline_phase: string;
  semaphore_state: string;
  entered_state_at: string;
  capital_allocated_pct: string;
  risk_per_trade_pct: string;
  sizing_multiplier: string;
  sizing_current_pct: string;
  kelly_fraction: string | null;
  created_at: string;
  baseline_id: number | null;
}

export function getBots(): Promise<BotRow[]> {
  return apiFetch<BotRow[]>("/api/v1/bots");
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
