import { useQuery } from "@tanstack/react-query";

import {
  getExposure,
  getExposureByCurrency,
  getMonteCarlo,
  getMonteCarloHistory,
  getTailRisk,
} from "@/api/endpoints/risk";

export function useTailRisk() {
  return useQuery({ queryKey: ["risk-tail"], queryFn: getTailRisk });
}

export function useExposure() {
  return useQuery({ queryKey: ["risk-exposure"], queryFn: getExposure });
}

export function useExposureByCurrency() {
  return useQuery({ queryKey: ["risk-exposure-by-currency"], queryFn: getExposureByCurrency });
}

export function useMonteCarlo(botId: number) {
  return useQuery({ queryKey: ["risk-montecarlo", botId], queryFn: () => getMonteCarlo(botId) });
}

export function useMonteCarloHistory(botId: number) {
  return useQuery({
    queryKey: ["risk-montecarlo-history", botId],
    queryFn: () => getMonteCarloHistory(botId),
  });
}
