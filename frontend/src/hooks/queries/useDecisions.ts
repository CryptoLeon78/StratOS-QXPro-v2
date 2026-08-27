import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  confirmDecision,
  dismissDecision,
  listDecisions,
  postponeDecision,
  type Decision,
} from "@/api/endpoints/decisions";
import { HEADER_SUMMARY_QUERY_KEY } from "@/hooks/queries/useHeaderSummary";

export function decisionsQueryKey(status?: Decision["status"]) {
  return ["decisions", status ?? "all"];
}

export function useDecisions(status?: Decision["status"]) {
  return useQuery({
    queryKey: decisionsQueryKey(status),
    queryFn: () => listDecisions(status),
  });
}

// confirm/postpone/dismiss invalidan la propia lista de decisiones Y el
// header summary (pending_decisions/alerts cambian con cada resolucion).
export function useDecisionMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["decisions"] });
    queryClient.invalidateQueries({ queryKey: HEADER_SUMMARY_QUERY_KEY });
  };

  return {
    confirm: useMutation({ mutationFn: confirmDecision, onSuccess: invalidate }),
    postpone: useMutation({
      mutationFn: ({ id, postponeUntil }: { id: number; postponeUntil: string }) =>
        postponeDecision(id, postponeUntil),
      onSuccess: invalidate,
    }),
    dismiss: useMutation({ mutationFn: dismissDecision, onSuccess: invalidate }),
  };
}
