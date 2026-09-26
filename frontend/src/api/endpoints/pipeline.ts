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

export interface OperationalQueueEntry {
  rank: number;
  strategy_name: string;
  symbol: string | null;
  timeframe: string | null;
  state: string;
}

export interface OperationalQueue {
  status: "READY" | "ABSENT" | "INVALID";
  detail: string | null;
  generated_at_utc: string | null;
  snapshot_sha256: string | null;
  entries: OperationalQueueEntry[];
}

export function getOperationalQueue(): Promise<OperationalQueue> {
  return apiFetch<OperationalQueue>("/api/v1/pipeline/operational-queue");
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

export interface DemoReadiness {
  candidate_id: number;
  ready: boolean;
  requirements: Array<{ key: string; satisfied: boolean }>;
  next_action: "DEMO_ATTACHMENT_REQUIRED" | "AUTOMATIC_F4_GATE";
}

export function checkDemoReadiness(candidateId: number): Promise<DemoReadiness> {
  return apiFetch<DemoReadiness>(`/api/v1/pipeline/${candidateId}/demo-readiness`, {
    method: "POST",
  });
}

export interface PipelineWorkItem {
  id: number;
  kind: string;
  source_key: string;
  phase: string;
  status: string;
  payload: Record<string, unknown>;
  retired_at: string | null;
}

export function createPipelineWorkItem(body: {
  kind: string;
  source_key: string;
  phase: string;
  payload: Record<string, unknown>;
}): Promise<PipelineWorkItem> {
  return apiFetch<PipelineWorkItem>("/api/v1/pipeline-orchestrator/work-items", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getPipelineWorkItems(phase?: string): Promise<PipelineWorkItem[]> {
  const suffix = phase ? `?phase=${encodeURIComponent(phase)}` : "";
  return apiFetch<PipelineWorkItem[]>(`/api/v1/pipeline-orchestrator/work-items${suffix}`);
}

export function retirePipelineWorkItem(itemId: number): Promise<PipelineWorkItem> {
  return apiFetch<PipelineWorkItem>(`/api/v1/pipeline-orchestrator/work-items/${itemId}/retire`, {
    method: "POST",
  });
}

export function requestPipelineCommand(
  itemId: number,
  body: { command_type: string; payload: Record<string, unknown>; idempotency_key: string; confirmed?: boolean }
): Promise<{ id: number; status: string }> {
  return apiFetch<{ id: number; status: string }>(
    `/api/v1/pipeline-orchestrator/work-items/${itemId}/commands`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export interface StaticValidatedAsset {
  id: number;
  strategy_name: string | null;
  symbol: string | null;
  timeframe: string | null;
  sqx_sha256: string | null;
  mql5_sha256: string | null;
}

export function getStaticValidatedAssets(offset = 0, limit = 100): Promise<StaticValidatedAsset[]> {
  return apiFetch<StaticValidatedAsset[]>(
    `/api/v1/pipeline-orchestrator/static-assets?offset=${offset}&limit=${limit}`
  );
}

export function enqueueF2Batch(assetIds: number[]): Promise<Array<{ id: number; asset_id: number; status: string }>> {
  return apiFetch<Array<{ id: number; asset_id: number; status: string }>>(
    "/api/v1/pipeline-orchestrator/f2/backtest-batches",
    { method: "POST", body: JSON.stringify({ asset_ids: assetIds, idempotency_key: crypto.randomUUID() }) }
  );
}

export interface F3BacktestEvidence { asset_id: number; strategy_name: string | null; symbol: string | null; timeframe: string | null; evidence: Record<string, unknown>; occurred_at: string; }
export function getF3BacktestEvidence(): Promise<F3BacktestEvidence[]> { return apiFetch<F3BacktestEvidence[]>("/api/v1/pipeline-orchestrator/f3/backtest-evidence"); }

export interface F5IncubationObservation {
  candidate_id: number;
  bot_id: number;
  magic_number: number;
  current_phase: PipelinePhase;
  observation_started_at: string;
  tester_baseline: {
    profit_factor: number;
    expectancy_r: number;
    sharpe: number;
    max_dd_pct: string;
    created_at: string;
  } | null;
  demo_trade_count: number;
  demo_trade_first_open_at: string | null;
  demo_trade_last_close_at: string | null;
  valid_observation_days: number;
  ea_state: {
    mode: string;
    autotrading: boolean;
    ea_version: string;
    sizing_pct: string | null;
    last_ingested_at: string;
  } | null;
  latest_heartbeat_at: string | null;
  latest_equity: {
    ts: string;
    equity: string;
    balance: string;
    drawdown_pct: string;
  } | null;
  observation_status: string;
  missing_evidence: string[];
}

export function getF5Incubation(): Promise<F5IncubationObservation[]> {
  return apiFetch<F5IncubationObservation[]>("/api/v1/pipeline-orchestrator/f5/incubation");
}

export interface DemoAttachmentManifestInput {
  asset_id: number;
  account_login: string;
  magic_number: number;
  symbol: string;
  timeframe: string;
  ea_version: string;
  mql5_sha256: string;
  compiled_ex5_sha256: string;
  comment_identity: string;
  expert_relative_path: string;
  reporter_outbox: string;
  required_mode: "REAL";
  required_autotrading: true;
  required_sizing_pct: string;
}

export function registerDemoAttachment(
  candidateId: number,
  manifest: DemoAttachmentManifestInput
): Promise<DemoReadiness> {
  return apiFetch<DemoReadiness>(`/api/v1/pipeline/${candidateId}/demo-attachment`, {
    method: "POST",
    body: JSON.stringify({ manifest }),
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
