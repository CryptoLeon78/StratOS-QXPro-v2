import { useQuery } from "@tanstack/react-query";

import { getAlerts } from "@/api/endpoints/alerts";

export function useAlerts(module?: string, includeResolved = false) {
  return useQuery({
    queryKey: ["alerts", module, includeResolved],
    queryFn: () => getAlerts(module, includeResolved),
  });
}
