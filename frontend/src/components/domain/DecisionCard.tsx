import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { PostponeDialog } from "@/components/domain/PostponeDialog";
import { useDecisionMutations } from "@/hooks/queries/useDecisions";
import type { Decision } from "@/api/endpoints/decisions";
import uiStrings from "@/styles/ui_strings.es.json";

interface DecisionCardProps {
  decision: Decision;
}

// PARTE 7.1/11.3: DecisionCard -- titulo, descripcion, instruccion MT en
// bloque mono, "Ver evidencia" colapsable, Confirmar/Posponer/Descartar.
export function DecisionCard({ decision }: DecisionCardProps) {
  const [postponeOpen, setPostponeOpen] = useState(false);
  const { confirm, postpone, dismiss } = useDecisionMutations();

  return (
    <Card className="border-l-2 border-l-accent-primary">
      <CardContent className="space-y-2 pt-4">
        <h3 className="font-semibold text-text-primary">{decision.title}</h3>
        <p className="text-sm text-text-secondary">{decision.description}</p>
        <p className="rounded-md bg-bg-surfaceRaised px-3 py-2 font-mono text-xs text-text-primary">
          {uiStrings.decisionCard.instructionPrefix}
          {decision.instruction_text}
        </p>
        {decision.evidence && (
          <Collapsible>
            <CollapsibleTrigger className="text-xs font-medium text-accent-primary hover:underline">
              {uiStrings.decisionCard.seeEvidence}
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-1 text-xs text-text-secondary">
              {Object.entries(decision.evidence).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <span className="font-medium text-text-primary">{key}:</span>
                  <span>{String(value)}</span>
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
        <div className="flex gap-2 pt-1">
          <Button size="sm" disabled={confirm.isPending} onClick={() => confirm.mutate(decision.id)}>
            {uiStrings.decisionCard.confirm}
          </Button>
          <Button size="sm" variant="outline" onClick={() => setPostponeOpen(true)}>
            {uiStrings.decisionCard.postpone}
          </Button>
          <Button size="sm" variant="outline" disabled={dismiss.isPending} onClick={() => dismiss.mutate(decision.id)}>
            {uiStrings.decisionCard.dismiss}
          </Button>
        </div>
      </CardContent>
      <PostponeDialog
        open={postponeOpen}
        onOpenChange={setPostponeOpen}
        isPending={postpone.isPending}
        onConfirm={(postponeUntil) => {
          postpone.mutate(
            { id: decision.id, postponeUntil },
            { onSuccess: () => setPostponeOpen(false) }
          );
        }}
      />
    </Card>
  );
}
