import { Badge } from "@/components/ui/badge";

// VERDE/AMARILLO/NARANJA (core/db/enums.py::SemaphoreState) -- mismo mapeo
// de color que AppHeader (semaphore global), extraido aqui porque G7 lo
// reutiliza en Salud/Bots/Riesgo.
const VARIANT: Record<string, "success" | "warning" | "orange"> = {
  VERDE: "success",
  AMARILLO: "warning",
  NARANJA: "orange",
};

function capitalize(value: string): string {
  return value.charAt(0) + value.slice(1).toLowerCase();
}

export function SemaphoreBadge({ state }: { state: string }) {
  return <Badge variant={VARIANT[state] ?? "default"}>{capitalize(state)}</Badge>;
}
