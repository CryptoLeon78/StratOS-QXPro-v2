import { apiFetch } from "@/api/client";

// Espejo 1:1 de DecisionResponse (core-engine/src/core/routers/decisions.py)
export interface Decision {
  id: number;
  ts: string;
  module: string;
  title: string;
  description: string;
  instruction_text: string;
  evidence: Record<string, unknown> | null;
  status: "PENDING" | "CONFIRMED" | "POSTPONED" | "DISMISSED";
  decided_at: string | null;
  decided_by: string | null;
  postpone_until: string | null;
}

export function listDecisions(status?: Decision["status"]): Promise<Decision[]> {
  const query = status ? `?decision_status=${status}` : "";
  return apiFetch<Decision[]>(`/api/v1/decisions${query}`);
}

export function confirmDecision(id: number): Promise<Decision> {
  return apiFetch<Decision>(`/api/v1/decisions/${id}/confirm`, { method: "POST" });
}

export function postponeDecision(id: number, postponeUntil: string): Promise<Decision> {
  return apiFetch<Decision>(`/api/v1/decisions/${id}/postpone`, {
    method: "POST",
    body: JSON.stringify({ postpone_until: postponeUntil }),
  });
}

export function dismissDecision(id: number): Promise<Decision> {
  return apiFetch<Decision>(`/api/v1/decisions/${id}/dismiss`, { method: "POST" });
}
