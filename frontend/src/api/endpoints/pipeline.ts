import { apiFetch } from "@/api/client";

export type PipelinePhase = "F1" | "F2" | "F3" | "F4" | "F5" | "F6" | "F7" | "PRODUCCION" | "CEMENTERIO";

// Espejo 1:1 de CandidateResponse (core-engine/src/core/routers/pipeline.py)
// -- solo los campos que el panel de Resumen usa (contadores por fase).
export interface PipelineCandidate {
  id: number;
  bot_id: number;
  current_phase: PipelinePhase;
}

export function getPipelineBoard(): Promise<PipelineCandidate[]> {
  return apiFetch<PipelineCandidate[]>("/api/v1/pipeline/board");
}
