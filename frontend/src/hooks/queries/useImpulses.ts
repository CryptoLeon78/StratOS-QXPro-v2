import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createImpulse } from "@/api/endpoints/impulses";

export function useCreateImpulse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createImpulse,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["impulses"] }),
  });
}
