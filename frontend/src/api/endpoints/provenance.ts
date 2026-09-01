import { apiFetch } from "@/api/client";

// Espejo 1:1 de core/routers/header.py::DataProvenanceResponse.
export type DataOrigin = "BROKER_REAL" | "BROKER_DEMO" | "FIXTURE";

export interface ProvenanceRow {
  data_origin: DataOrigin;
  accounts: number;
  bots: number;
}

export interface DataProvenance {
  accounts: ProvenanceRow[];
  is_mixed: boolean;
}

export function getDataProvenance(): Promise<DataProvenance> {
  return apiFetch<DataProvenance>("/data-provenance");
}
