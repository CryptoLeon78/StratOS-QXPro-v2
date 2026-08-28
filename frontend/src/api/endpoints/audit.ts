import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/audit.py.
export interface ReconciliationRow {
  account_id: number;
  initial_balance: string;
  flows: string;
  final_balance: string;
  expected: string;
  discrepancy_pct: string | null;
  breached: boolean;
}

export function getAuditStatus(): Promise<ReconciliationRow[]> {
  return apiFetch<ReconciliationRow[]>("/api/v1/audit/status");
}

export function runAuditNow(): Promise<ReconciliationRow[]> {
  return apiFetch<ReconciliationRow[]>("/api/v1/audit/run", { method: "POST" });
}

export interface SealsSummary {
  total_batches: number;
  total_trades: number;
  ticket_min: number | null;
  ticket_max: number | null;
  history_start: string | null;
  history_end: string | null;
}

export function getSealsSummary(): Promise<SealsSummary> {
  return apiFetch<SealsSummary>("/api/v1/audit/seals");
}

// G10: "Tramos sin envío" detallados -- espejo 1:1 de
// ContinuityGapsResponse/ContinuityGapResponse.
export interface ContinuityGap {
  start: string;
  end: string;
  duration_minutes: number;
}

export interface ContinuityGaps {
  account_id: number;
  coverage_pct: number;
  gaps: ContinuityGap[];
}

export function getContinuityGaps(): Promise<ContinuityGaps[]> {
  return apiFetch<ContinuityGaps[]>("/api/v1/audit/continuity-gaps");
}
