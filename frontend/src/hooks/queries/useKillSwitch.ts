import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { confirmKillSwitchDeescalation, getKillSwitchStatus } from "@/api/endpoints/killswitch";
import { HEADER_SUMMARY_QUERY_KEY } from "@/hooks/queries/useHeaderSummary";

export const KILLSWITCH_STATUS_QUERY_KEY = ["killswitch-status"];

export function useKillSwitchStatus() {
  return useQuery({ queryKey: KILLSWITCH_STATUS_QUERY_KEY, queryFn: getKillSwitchStatus });
}

// P6.2: unica ruta de desescalado, firma con el email del usuario en el
// propio backend -- invalida el header (ks_level/portfolio_dd_pct viven
// tambien ahi).
export function useConfirmDeescalation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: confirmKillSwitchDeescalation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KILLSWITCH_STATUS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: HEADER_SUMMARY_QUERY_KEY });
    },
  });
}
