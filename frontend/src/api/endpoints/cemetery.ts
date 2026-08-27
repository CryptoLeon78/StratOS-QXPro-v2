import { apiFetch } from "@/api/client";
import { ApiError } from "@/api/client";

// Espejo 1:1 de core/routers/cemetery.py. Fecha de inicio del rango NO esta
// en el schema, solo `retired_at` (docs/backlog.md).
export interface CemeteryEntry {
  id: number;
  bot_id: number;
  retired_at: string;
  cause: string;
  autopsy_text: string;
  lesson: string;
  revalidation_from_phase: string;
  reactivation_blocked: boolean;
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
