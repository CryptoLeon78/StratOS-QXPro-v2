import { useQuery } from "@tanstack/react-query";

import { getHeartbeat, getTca, getWatchdog } from "@/api/endpoints/execution";

export function useWatchdog() {
  return useQuery({ queryKey: ["execution-watchdog"], queryFn: getWatchdog });
}

export function useHeartbeat() {
  return useQuery({ queryKey: ["execution-heartbeat"], queryFn: getHeartbeat });
}

export function useTca() {
  return useQuery({ queryKey: ["execution-tca"], queryFn: getTca });
}
