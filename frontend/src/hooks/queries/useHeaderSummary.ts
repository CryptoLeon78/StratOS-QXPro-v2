import { useQuery } from "@tanstack/react-query";

import { getHeaderSummary } from "@/api/endpoints/header";

export const HEADER_SUMMARY_QUERY_KEY = ["header-summary"];

// refetchInterval de respaldo (polling 5s, PARTE 7.1) -- se sustituye por
// invalidacion via WS en el commit del cliente WS; hasta entonces, esto
// es lo unico que mantiene la cabecera fresca.
export function useHeaderSummary() {
  return useQuery({
    queryKey: HEADER_SUMMARY_QUERY_KEY,
    queryFn: getHeaderSummary,
    refetchInterval: 5000,
  });
}
