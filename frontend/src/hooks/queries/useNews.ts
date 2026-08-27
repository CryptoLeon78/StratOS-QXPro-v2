import { useQuery } from "@tanstack/react-query";

import { getNewsShield } from "@/api/endpoints/news";

export function useNewsShield(hours = 48) {
  return useQuery({ queryKey: ["news-shield", hours], queryFn: () => getNewsShield(hours) });
}
