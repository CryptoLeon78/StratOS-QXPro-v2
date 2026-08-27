import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/impulses.py -- "Diario de impulsos" (M7),
// boton "Tengo el impulso de intervenir" en Bots (7.4) y Resumen.
export type ImpulseAction =
  | "PAUSE_BOT"
  | "CLOSE_POSITION"
  | "INCREASE_RISK"
  | "DECREASE_RISK"
  | "OTHER";

export interface ImpulseRow {
  id: number;
  ts: string;
  bot_id: number;
  description: string;
  desired_action: ImpulseAction;
  executed: boolean;
  status: "PENDING" | "EVALUATING" | "CLOSED";
  counterfactual_result_7d_eur: string | null;
  avoided_cost_eur: string | null;
  evaluated_at: string | null;
}

export function getImpulses(): Promise<ImpulseRow[]> {
  return apiFetch<ImpulseRow[]>("/api/v1/impulses");
}

export function createImpulse(body: {
  bot_id: number;
  description: string;
  desired_action: ImpulseAction;
}): Promise<ImpulseRow> {
  return apiFetch<ImpulseRow>("/api/v1/impulses", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
