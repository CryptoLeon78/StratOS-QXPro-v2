import { Badge } from "@/components/ui/badge";

// WatchdogState (core/formulas/types.py) -- pestana Ejecucion (7.6).
const VARIANT: Record<string, "success" | "warning" | "danger" | "info"> = {
  OK: "success",
  DEAD: "danger",
  RUNAWAY: "danger",
  OUT_OF_TOLERANCE: "warning",
  INSUFFICIENT_DATA: "info",
};

export function WatchdogStateBadge({ state }: { state: string }) {
  return <Badge variant={VARIANT[state] ?? "default"}>{state}</Badge>;
}
