import { useQuery } from "@tanstack/react-query";

import { getEquityCurve, type EquityRange } from "@/api/endpoints/header";

export function useEquityCurve(range: EquityRange) {
  return useQuery({
    queryKey: ["equity-curve", range],
    queryFn: () => getEquityCurve(range),
  });
}
