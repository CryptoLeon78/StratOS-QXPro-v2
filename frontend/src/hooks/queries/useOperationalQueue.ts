import { useQuery } from "@tanstack/react-query";

import { getOperationalQueue } from "@/api/endpoints/pipeline";

export function useOperationalQueue() {
  return useQuery({
    queryKey: ["operational-tester-queue"],
    queryFn: getOperationalQueue,
    refetchInterval: 5000,
  });
}
