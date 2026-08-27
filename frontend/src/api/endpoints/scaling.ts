import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/scaling.py::UmsPhaseResponse. `metrics` es
// JSON libre -- lo que services/ums.py realmente popula ahi se verifica en
// el propio commit de la pestana Escalado, no se asume aqui.
export interface UmsPhaseLogRow {
  id: number;
  ts: string;
  phase: number;
  equity_at: string;
  metrics: Record<string, unknown>;
  ready_to_advance: boolean;
  signed_by: string | null;
}

export function getCurrentUmsPhase(): Promise<UmsPhaseLogRow | null> {
  return apiFetch<UmsPhaseLogRow | null>("/api/v1/scaling/ums");
}

export function getUmsMonthlyHistory(): Promise<UmsPhaseLogRow[]> {
  return apiFetch<UmsPhaseLogRow[]>("/api/v1/scaling/monthly");
}
