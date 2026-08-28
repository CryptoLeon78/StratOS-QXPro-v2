import { useQuery } from "@tanstack/react-query";

import { getNewsShield, getNewsShieldTrades } from "@/api/endpoints/news";

export function useNewsShield(hours = 48) {
  return useQuery({ queryKey: ["news-shield", hours], queryFn: () => getNewsShield(hours) });
}

export function useNewsShieldTrades() {
  return useQuery({ queryKey: ["news-shield-trades"], queryFn: getNewsShieldTrades });
}
