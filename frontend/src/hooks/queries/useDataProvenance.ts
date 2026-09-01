import { useQuery } from "@tanstack/react-query";

import { getDataProvenance } from "@/api/endpoints/provenance";

export const DATA_PROVENANCE_QUERY_KEY = ["data-provenance"];

// La composicion de procedencia cambia sólo al dar de alta o retirar una cuenta,
// asi que no necesita el polling de 5s de la cabecera.
export function useDataProvenance() {
  return useQuery({
    queryKey: DATA_PROVENANCE_QUERY_KEY,
    queryFn: getDataProvenance,
    staleTime: 60_000,
  });
}
