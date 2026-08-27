import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createCandidate, killCandidate, promoteCandidate } from "@/api/endpoints/pipeline";

export function usePipelineActions() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["pipeline-board"] });

  return {
    promote: useMutation({ mutationFn: promoteCandidate, onSuccess: invalidate }),
    create: useMutation({ mutationFn: createCandidate, onSuccess: invalidate }),
    kill: useMutation({
      mutationFn: ({
        candidateId,
        body,
      }: {
        candidateId: number;
        body: { cause: string; autopsy_text: string; lesson: string };
      }) => killCandidate(candidateId, body),
      onSuccess: invalidate,
    }),
  };
}
