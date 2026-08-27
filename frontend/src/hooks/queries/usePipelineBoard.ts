import { useQuery } from "@tanstack/react-query";

import { getPipelineBoard } from "@/api/endpoints/pipeline";

export function usePipelineBoard() {
  return useQuery({
    queryKey: ["pipeline-board"],
    queryFn: getPipelineBoard,
  });
}
