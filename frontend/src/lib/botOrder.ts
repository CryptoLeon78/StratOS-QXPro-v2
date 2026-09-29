import type { BotRow } from "@/api/endpoints/bots";

// Orden operativo: lo que esta en produccion primero, luego las fases de
// incubacion de la mas avanzada a la menos, y el archivo al final.
const PHASE_ORDER = ["F7", "PRODUCCION", "F6", "F5", "F4", "F3", "F2", "F1", "CEMENTERIO"];
export const SEMAPHORE_FILTERS = ["ALL", "VERDE", "AMARILLO", "NARANJA"] as const;

export function sortBotsForList(bots: BotRow[]): BotRow[] {
  const rank = (phase: string) => {
    const index = PHASE_ORDER.indexOf(phase);
    return index === -1 ? PHASE_ORDER.length : index;
  };
  return [...bots].sort(
    (a, b) => rank(a.pipeline_phase) - rank(b.pipeline_phase) || a.name.localeCompare(b.name)
  );
}
