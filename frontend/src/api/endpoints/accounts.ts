import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/accounts.py. Equity/balance/margen libre NO
// estan en AccountResponse (docs/backlog.md); heartbeat/uptime se piden
// aparte via execution.ts::getHeartbeat (mismo account_id).
export interface AccountRow {
  id: number;
  name: string;
  broker: string;
  login: string;
  server: string;
  currency: string;
  is_demo: boolean;
  is_active: boolean;
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
  last_ingested_at: string;
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
}

export function getAccountsDrift(): Promise<DriftRow[]> {
  return apiFetch<DriftRow[]>("/api/v1/accounts/drift");
}
