import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getAuditStatus, getSealsSummary, runAuditNow } from "@/api/endpoints/audit";

export function useAuditStatus() {
  return useQuery({ queryKey: ["audit-status"], queryFn: getAuditStatus });
}

export function useSealsSummary() {
  return useQuery({ queryKey: ["audit-seals"], queryFn: getSealsSummary });
}

export function useRunAudit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: runAuditNow,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audit-status"] }),
  });
}
