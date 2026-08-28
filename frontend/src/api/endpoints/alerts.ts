import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/alerts.py::AlertResponse (G10, grupo n).
export interface AlertRow {
  id: number;
  ts: string;
  level: "INFO" | "SUAVE" | "CRITICA";
  module: string;
  message: string;
  action_required: string | null;
  resolved: boolean;
  resolved_at: string | null;
}

export function getAlerts(module?: string, includeResolved = false): Promise<AlertRow[]> {
  const params = new URLSearchParams();
  if (module) params.set("module", module);
  if (includeResolved) params.set("include_resolved", "true");
  const query = params.toString();
  return apiFetch<AlertRow[]>(`/api/v1/alerts${query ? `?${query}` : ""}`);
}
