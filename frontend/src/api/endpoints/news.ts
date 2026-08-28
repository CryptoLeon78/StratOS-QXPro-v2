import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/news.py::NewsShieldRow.
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

// G10: "Trades en ventana de noticias (30 dias)" -- espejo 1:1 de
// TradeInNewsWindowResponse. Default de dias ya es 30 en el backend
// (_SHIELD_TRADES_DEFAULT_DAYS), sin parametro.
export interface TradeInNewsWindow {
  trade_id: number;
  symbol: string;
  bot_name: string | null;
  open_time: string;
  close_time: string | null;
  news_event_id: number;
  news_title: string;
  news_ts: string;
}

export function getNewsShieldTrades(): Promise<TradeInNewsWindow[]> {
  return apiFetch<TradeInNewsWindow[]>("/api/v1/news/shield/trades");
}
