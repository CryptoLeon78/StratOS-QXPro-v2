import { apiFetch } from "@/api/client";

export type PipelinePhase =
  | "F1"
  | "F2"
  | "F3"
  | "F4"
  | "F5"
  | "F6"
  | "F7"
  | "PRODUCCION"
  | "CEMENTERIO";

// Espejo 1:1 de CandidateResponse (core-engine/src/core/routers/pipeline.py).
// gates_passed/gates_total son el conteo agregado -- el desglose por
// criterio se recalcula en frontend (ADR, ver PipelineGateChecklist) a
// partir de estos mismos campos crudos + los umbrales de /config/pipeline-gate.
export interface PipelineCandidate {
  id: number;
  bot_id: number;
  account_id: number;
  account_origin: "BROKER_REAL" | "BROKER_DEMO" | "FIXTURE";
  bot_origin: "EXTERNAL_PRODUCTION" | "INCUBATION" | "ANALYSIS";
  current_phase: PipelinePhase;
  entered_phase_at: string;
  incubation_days: number;
  oos_trades: number;
  profit_factor: number | null;
  expectancy_r: number | null;
  sharpe: number | null;
  max_dd_pct: string | null;
  wfe: number | null;
  trades_per_week: number | null;
  gates_passed: number;
  gates_total: number;
  provisional: boolean;
  verdict: "GO" | "HOLD" | "KILL" | null;
  verdict_reason: string | null;
  decision_eta_days: number | null;
  evaluated_at: string | null;
  backtest_vs_forward?: BacktestVsForward | null;
}

export interface BacktestVsForward {
  backtest: { profit_factor: number; expectancy_r: number; sharpe: number; max_dd_pct: string };
  forward: { profit_factor: number | null; expectancy_r: number | null; sharpe: number | null; max_dd_pct: string | null };
  baseline_created_at: string;
  baseline_provenance: string | null;
  delta_profit_factor: number | null;
  delta_expectancy_r: number | null;
  delta_sharpe: number | null;
  delta_max_dd_pct: string | null;
}

export function getPipelineBoard(): Promise<PipelineCandidate[]> {
  return apiFetch<PipelineCandidate[]>("/api/v1/pipeline/board");
}

// Scoped variant for account/provenance-aware views. The parameterless board
// function remains a valid TanStack Query queryFn.
export function getScopedPipelineBoard(
  accountId?: number,
  dataOrigin?: PipelineCandidate["account_origin"]
): Promise<PipelineCandidate[]> {
  const params = new URLSearchParams();
  if (accountId !== undefined) params.set("account_id", String(accountId));
  if (dataOrigin !== undefined) params.set("data_origin", dataOrigin);
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiFetch<PipelineCandidate[]>(`/api/v1/pipeline/board${suffix}`);
}

export function promoteCandidate(candidateId: number): Promise<PipelineCandidate> {
  return apiFetch<PipelineCandidate>(`/api/v1/pipeline/${candidateId}/promote`, {
    method: "POST",
  });
}

export function createCandidate(botId: number): Promise<PipelineCandidate> {
  return apiFetch<PipelineCandidate>("/api/v1/pipeline/candidates", {
    method: "POST",
    body: JSON.stringify({ bot_id: botId }),
  });
}

export interface CemeteryEntry {
  id: number;
  bot_id: number;
  retired_at: string;
  cause: string;
  autopsy_text: string;
  lesson: string;
  revalidation_from_phase: PipelinePhase;
  reactivation_blocked: boolean;
}

export function killCandidate(
  candidateId: number,
  body: { cause: string; autopsy_text: string; lesson: string }
): Promise<CemeteryEntry> {
  return apiFetch<CemeteryEntry>(`/api/v1/pipeline/${candidateId}/kill`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
