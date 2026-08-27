import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/news.py::NewsShieldRow. "Trades en ventana de
// noticias (30 dias)" NO esta en este schema (docs/backlog.md).
export interface NewsShieldRow {
  id: number;
  ts: string;
  currency: string;
  impact: "LOW" | "MEDIUM" | "HIGH";
  title: string;
  source: string;
  window_start: string;
  window_end: string;
  affected_bots: string[];
}

export function getNewsShield(hours = 48): Promise<NewsShieldRow[]> {
  return apiFetch<NewsShieldRow[]>(`/api/v1/news/shield?hours=${hours}`);
}
