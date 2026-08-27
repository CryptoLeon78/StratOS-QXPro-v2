import { useQuery } from "@tanstack/react-query";

import { getHeartbeat, getWatchdog } from "@/api/endpoints/execution";

export function useWatchdog() {
  return useQuery({ queryKey: ["execution-watchdog"], queryFn: getWatchdog });
}

export function useHeartbeat() {
  return useQuery({ queryKey: ["execution-heartbeat"], queryFn: getHeartbeat });
}
