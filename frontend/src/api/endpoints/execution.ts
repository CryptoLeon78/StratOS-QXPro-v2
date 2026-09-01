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

export interface TcaSummary {
  fills: number;
  slippage_p50: string | null;
  slippage_p95: string | null;
  slippage_p99: string | null;
  asymmetry_index: number | null;
  implementation_shortfall_p50: string | null;
  rejected_orders: number;
  broker_profiles: BrokerProfile[];
}

export interface BrokerProfile {
  broker: string;
  symbol: string;
  fills: number;
  spread_p50: string | null;
}

export function getTca(): Promise<TcaSummary | null> {
  return apiFetch<TcaSummary | null>("/api/v1/execution/tca");
}
