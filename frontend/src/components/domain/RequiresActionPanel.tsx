import { DecisionCard } from "@/components/domain/DecisionCard";
import { useDecisions } from "@/hooks/queries/useDecisions";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.1: panel "Requiere accion (N)" -- contra
// GET /api/v1/decisions?decision_status=PENDING.
export function RequiresActionPanel() {
  const { data, isLoading } = useDecisions("PENDING");
  const decisions = data ?? [];

  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-text-primary">
        {interpolate(uiStrings.decisionCard.requiresAction, { count: decisions.length })}
      </h2>
      {!isLoading && decisions.length === 0 && (
        <p className="text-sm text-text-secondary">{uiStrings.decisionCard.emptyState}</p>
      )}
      <div className="space-y-3">
        {decisions.map((decision) => (
          <DecisionCard key={decision.id} decision={decision} />
        ))}
      </div>
    </div>
  );
}
