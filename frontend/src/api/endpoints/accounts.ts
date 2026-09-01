import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/accounts.py. equity/balance/free_margin/
// margin_level (G10): el EquitySnapshot mas reciente por account_id --
// `null` si la cuenta nunca reporto uno, nunca inventado. heartbeat/uptime
// se piden aparte via execution.ts::getHeartbeat (mismo account_id).
export interface AccountRow {
  id: number;
  name: string;
  broker: string;
  login: string;
  server: string;
  currency: string;
  is_demo: boolean;
  data_origin: "BROKER_REAL" | "BROKER_DEMO" | "FIXTURE";
  is_active: boolean;
  equity: string | null;
  balance: string | null;
  free_margin: string | null;
  margin_level: number | null;
  equity_ts: string | null;
}

export function getAccounts(): Promise<AccountRow[]> {
  return apiFetch<AccountRow[]>("/api/v1/accounts");
}

export interface EaStateRow {
  magic_number: number;
  ea_version: string;
  mode: string;
  autotrading: boolean;
  schedule_filter: Record<string, unknown> | null;
  news_windows: unknown[] | null;
  sizing_pct: string | null;
  last_ingested_at: string;
  ea_required_version: string | null;
  version_verifiable: boolean;
  version_matches: boolean | null;
}

export function getAccountEas(accountId: number): Promise<EaStateRow[]> {
  return apiFetch<EaStateRow[]>(`/api/v1/accounts/${accountId}/eas`);
}

export interface DriftRow {
  bot_id: number;
  account_id: number;
  magic_number: number;
  expected_mode: string;
  reported_mode: string;
  drift: boolean;
  expected_autotrading: boolean;
  reported_autotrading: boolean;
  autotrading_drift: boolean;
  expected_sizing_pct: string;
  reported_sizing_pct: string | null;
  sizing_drift: boolean | null;
}

export function getAccountsDrift(): Promise<DriftRow[]> {
  return apiFetch<DriftRow[]>("/api/v1/accounts/drift");
}
