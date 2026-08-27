import { useQuery } from "@tanstack/react-query";

import { getExposure, getMonteCarlo, getTailRisk } from "@/api/endpoints/risk";

export function useTailRisk() {
  return useQuery({ queryKey: ["risk-tail"], queryFn: getTailRisk });
}

export function useExposure() {
  return useQuery({ queryKey: ["risk-exposure"], queryFn: getExposure });
}

export function useMonteCarlo(botId: number) {
  return useQuery({ queryKey: ["risk-montecarlo", botId], queryFn: () => getMonteCarlo(botId) });
}
