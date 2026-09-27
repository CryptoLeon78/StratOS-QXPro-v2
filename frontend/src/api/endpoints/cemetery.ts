import { apiFetch } from "@/api/client";
import { ApiError } from "@/api/client";

// Espejo 1:1 de core/routers/cemetery.py. `entered_pipeline_at` sale del
// rastro append-only PipelinePhaseTransition (existe desde G11, docs/adr/0006):
// null para un bot retirado sin ese rastro (admitido antes de G11, o sembrado
// directo en produccion sin pasar por F1-F7) -- ausencia declarada, nunca se
// sustituye por otra fecha.
export interface CemeteryEntry {
  id: number;
  bot_id: number;
  retired_at: string;
  cause: string;
  autopsy_text: string;
  lesson: string;
  revalidation_from_phase: string;
  reactivation_blocked: boolean;
  entered_pipeline_at: string | null;
}

export function getCemetery(): Promise<CemeteryEntry[]> {
  return apiFetch<CemeteryEntry[]>("/api/v1/cemetery");
}

// SIEMPRE 409 (evaluate_cemetery_reactivation esta disenada para rechazar
// cualquier input, PARTE 6.3 "sin retorno") -- se llama solo para mostrar
// el motivo exacto que devuelve el backend, nunca esperando un 200.
export async function attemptReactivation(botId: number): Promise<string> {
  try {
    await apiFetch(`/api/v1/cemetery/${botId}/reactivate`, { method: "POST" });
    throw new Error("reactivacion inesperadamente permitida -- esto nunca deberia pasar");
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      return error.detail ?? error.message;
    }
    throw error;
  }
}
