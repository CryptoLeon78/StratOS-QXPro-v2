import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { attemptReactivation, getCemetery } from "@/api/endpoints/cemetery";

export function useCemetery() {
  return useQuery({ queryKey: ["cemetery"], queryFn: getCemetery });
}

// PARTE 6.3 "API 409 siempre; sin control en UI": esta mutation NUNCA
// tiene un caso de exito real -- solo existe para mostrar el motivo del
// 409 (attemptReactivation ya lo resuelve como valor de retorno, nunca
// lanza en el camino esperado).
export function useAttemptReactivation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: attemptReactivation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cemetery"] }),
  });
}
