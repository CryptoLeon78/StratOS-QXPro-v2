import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/killswitch.py. `/confirm` es la UNICA ruta de
// desescalado (P6.2) -- firma con el email del usuario autenticado, tomado
// del JWT en el propio backend (no se envia desde el frontend).
export interface KillSwitchStatus {
  level: number;
  portfolio_dd_pct: string | null;
  instruction_text: string | null;
  episode_max_dd_pct: string | null;
  episode_duration_seconds: number | null;
}

export function getKillSwitchStatus(): Promise<KillSwitchStatus> {
  return apiFetch<KillSwitchStatus>("/api/v1/killswitch/status");
}

export function confirmKillSwitchDeescalation(): Promise<KillSwitchStatus> {
  return apiFetch<KillSwitchStatus>("/api/v1/killswitch/confirm", { method: "POST" });
}
