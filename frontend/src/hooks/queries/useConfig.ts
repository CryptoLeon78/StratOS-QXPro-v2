import { useQuery } from "@tanstack/react-query";

import {
  getKillSwitchLadder,
  getPipelineGateThresholds,
  getSemaphoreInstructions,
  getUmsPhasesConfig,
} from "@/api/endpoints/config";

// Los 4 endpoints de core/routers/config.py (G7): estaticos, cambian solo
// si se toca thresholds.seed.json y se reinicia core-engine -- staleTime
// largo, no tiene sentido refetchear cada 5s como el resto de queries.
const STATIC_CONFIG_STALE_TIME_MS = 5 * 60 * 1000;

export function useKillSwitchLadder() {
  return useQuery({
    queryKey: ["config-killswitch-ladder"],
    queryFn: getKillSwitchLadder,
    staleTime: STATIC_CONFIG_STALE_TIME_MS,
  });
}

export function useUmsPhasesConfig() {
  return useQuery({
    queryKey: ["config-ums-phases"],
    queryFn: getUmsPhasesConfig,
    staleTime: STATIC_CONFIG_STALE_TIME_MS,
  });
}

export function usePipelineGateThresholds() {
  return useQuery({
    queryKey: ["config-pipeline-gate"],
    queryFn: getPipelineGateThresholds,
    staleTime: STATIC_CONFIG_STALE_TIME_MS,
  });
}

export function useSemaphoreInstructions() {
  return useQuery({
    queryKey: ["config-semaphore-instructions"],
    queryFn: getSemaphoreInstructions,
    staleTime: STATIC_CONFIG_STALE_TIME_MS,
  });
}
