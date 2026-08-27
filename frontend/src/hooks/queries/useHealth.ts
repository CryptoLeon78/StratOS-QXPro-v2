import { useQuery } from "@tanstack/react-query";

import { getHealthBots } from "@/api/endpoints/health";

export function useHealthBots() {
  return useQuery({ queryKey: ["health-bots"], queryFn: getHealthBots });
}
