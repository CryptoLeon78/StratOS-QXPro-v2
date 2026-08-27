import { Badge } from "@/components/ui/badge";

// GO/HOLD/KILL (core/db/enums.py::Verdict) -- pestana Pipeline (7.3).
const VARIANT: Record<string, "success" | "warning" | "danger"> = {
  GO: "success",
  HOLD: "warning",
  KILL: "danger",
};

export function VerdictBadge({ verdict }: { verdict: string }) {
  return <Badge variant={VARIANT[verdict] ?? "default"}>{verdict}</Badge>;
}
