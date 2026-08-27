import { Badge } from "@/components/ui/badge";
import { useDecisions } from "@/hooks/queries/useDecisions";
import { usePipelineBoard } from "@/hooks/queries/usePipelineBoard";
import { cn } from "@/lib/utils";
import uiStrings from "@/styles/ui_strings.es.json";
import type { PipelinePhase } from "@/api/endpoints/pipeline";

const COUNTED_PHASES: PipelinePhase[] = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"];

// module -> prefijo/color de "novedades". Diseno propio (PARTE 7.1 no da
// la regla exacta, solo el ejemplo visual) -- ver ASSUMPTIONS G6:
// module=="pipeline" viene de state_machines/pipeline.py (gate GO),
// module=="challenger" de challenger.py (rotacion/OVERSTAY), module==
// "semaphore" de semaphore.py (transicion a NARANJA).
const MODULE_TO_PREFIX: Record<string, { label: string; variant: "success" | "warning" | "orange" }> = {
  pipeline: { label: uiStrings.pipelinePanel.prefixGo, variant: "success" },
  challenger: { label: uiStrings.pipelinePanel.prefixOverstay, variant: "warning" },
  semaphore: { label: uiStrings.pipelinePanel.prefixNaranja, variant: "orange" },
};

export function PipelinePanel() {
  const { data: board } = usePipelineBoard();
  const { data: decisions } = useDecisions();

  const counts = Object.fromEntries(COUNTED_PHASES.map((phase) => [phase, 0])) as Record<
    PipelinePhase,
    number
  >;
  for (const candidate of board ?? []) {
    if (candidate.current_phase in counts) {
      counts[candidate.current_phase] += 1;
    }
  }

  const novedades = (decisions ?? []).filter((d) => d.module in MODULE_TO_PREFIX);

  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-text-primary">
        {uiStrings.pipelinePanel.title}
      </h2>
      <div className="mb-4 flex flex-wrap gap-1.5">
        {COUNTED_PHASES.map((phase) => (
          <Badge key={phase} variant="outline">
            {phase}: {counts[phase]}
          </Badge>
        ))}
      </div>
      <ul className="space-y-1.5">
        {novedades.map((decision) => {
          const prefix = MODULE_TO_PREFIX[decision.module];
          return (
            <li key={decision.id} className="text-xs text-text-secondary">
              <span
                className={cn(
                  "mr-1.5 font-semibold",
                  prefix.variant === "success" && "text-semantic-success",
                  prefix.variant === "warning" && "text-semantic-warning",
                  prefix.variant === "orange" && "text-semantic-orange"
                )}
              >
                {prefix.label}
              </span>
              {decision.title}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
