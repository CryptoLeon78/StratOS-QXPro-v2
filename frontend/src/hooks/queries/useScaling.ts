import { useQuery } from "@tanstack/react-query";

import { getCurrentUmsPhase, getUmsMonthlyHistory } from "@/api/endpoints/scaling";

export function useCurrentUmsPhase() {
  return useQuery({ queryKey: ["scaling-ums"], queryFn: getCurrentUmsPhase });
}

export function useUmsMonthlyHistory() {
  return useQuery({ queryKey: ["scaling-monthly"], queryFn: getUmsMonthlyHistory });
}
