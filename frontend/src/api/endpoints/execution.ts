import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/execution.py.
export interface WatchdogRow {
  bot_id: number;
  magic_number: number;
  state: "OK" | "DEAD" | "RUNAWAY" | "OUT_OF_TOLERANCE" | "INSUFFICIENT_DATA";
  observed_30d: number;
  expected_month: number | null;
  last_trade_at: string | null;
}

export function getWatchdog(): Promise<WatchdogRow[]> {
  return apiFetch<WatchdogRow[]>("/api/v1/execution/watchdog");
}

export interface HeartbeatRow {
  account_id: number;
  last_ts: string | null;
  latency_ms: number | null;
  uptime_pct_7d: number;
  connected: boolean;
}

export function getHeartbeat(): Promise<HeartbeatRow[]> {
  return apiFetch<HeartbeatRow[]>("/api/v1/execution/heartbeat");
}
