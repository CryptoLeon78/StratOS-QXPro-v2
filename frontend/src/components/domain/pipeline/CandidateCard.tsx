import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { GateChecklist } from "@/components/domain/pipeline/GateChecklist";
import { KillDialog } from "@/components/domain/pipeline/KillDialog";
import { VerdictBadge } from "@/components/domain/VerdictBadge";
import { useBot } from "@/hooks/queries/useBots";
import { usePipelineActions } from "@/hooks/queries/usePipelineActions";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { PipelineCandidate, PipelinePhase } from "@/api/endpoints/pipeline";

const MANUAL_PROMOTE_PHASES = new Set<PipelinePhase>(["F1", "F2", "F3"]);

function nextPhase(phase: PipelinePhase): number | null {
  const n = Number(phase.replace("F", ""));
  return Number.isFinite(n) ? n + 1 : null;
}

// PARTE 7.3: tarjeta de candidato del kanban. Boton "Promover" solo
// habilitado F1-F3 (P6.3: F4+ solo por gate automatico) -- el dropdown
// generico "Mover a..." de la captura se sustituye por los 2 botones
// reales (Promover/Matar), unicos que el backend soporta (ADR).
export function CandidateCard({ candidate }: { candidate: PipelineCandidate }) {
  const { data: bot } = useBot(candidate.bot_id);
  const { promote } = usePipelineActions();
  const [killOpen, setKillOpen] = useState(false);
  const canPromote = MANUAL_PROMOTE_PHASES.has(candidate.current_phase);
  const target = nextPhase(candidate.current_phase);

  return (
    <Card>
      <CardHeader className="space-y-1 p-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-text-primary">{bot?.name ?? `Bot #${candidate.bot_id}`}</p>
          {candidate.provisional && <Badge variant="outline">{uiStrings.pipeline.provisional}</Badge>}
        </div>
        <p className="text-xs text-text-secondary">
          {interpolate(uiStrings.pipeline.daysInPhase, { days: candidate.incubation_days })}
        </p>
        <p className="text-xs text-text-muted">
          {candidate.account_origin} · {candidate.bot_origin}
        </p>
      </CardHeader>
      <CardContent className="space-y-2 p-3 pt-0">
        <div className="flex items-center justify-between">
          {candidate.verdict && <VerdictBadge verdict={candidate.verdict} />}
          <span className="text-xs text-text-secondary">
            {interpolate(uiStrings.pipeline.gate, {
              passed: candidate.gates_passed,
              total: candidate.gates_total,
            })}
          </span>
        </div>
        {candidate.decision_eta_days !== null && (
          <p className="text-xs text-text-secondary">
            {interpolate(uiStrings.pipeline.decisionEta, { days: candidate.decision_eta_days })}
          </p>
        )}
        <Collapsible>
          <CollapsibleTrigger className="text-xs text-accent-primary">
            {uiStrings.pipeline.gateDetail}
          </CollapsibleTrigger>
          <CollapsibleContent>
            <GateChecklist candidate={candidate} />
          </CollapsibleContent>
        </Collapsible>
        <Collapsible>
          <CollapsibleTrigger className="text-xs text-accent-primary">
            {uiStrings.pipeline.backtestForwardTitle}
          </CollapsibleTrigger>
          <CollapsibleContent>
            {candidate.backtest_vs_forward ? (
              <div className="space-y-1 text-xs text-text-secondary">
                <p>{uiStrings.pipeline.backtestForwardBaseline}: PF {candidate.backtest_vs_forward.backtest.profit_factor.toFixed(2)} · Exp R {candidate.backtest_vs_forward.backtest.expectancy_r.toFixed(2)} · Sharpe {candidate.backtest_vs_forward.backtest.sharpe.toFixed(2)} · DD {candidate.backtest_vs_forward.backtest.max_dd_pct}%</p>
                <p>{uiStrings.pipeline.backtestForwardForward}: PF {candidate.backtest_vs_forward.forward.profit_factor?.toFixed(2) ?? "—"} · Exp R {candidate.backtest_vs_forward.forward.expectancy_r?.toFixed(2) ?? "—"} · Sharpe {candidate.backtest_vs_forward.forward.sharpe?.toFixed(2) ?? "—"} · DD {candidate.backtest_vs_forward.forward.max_dd_pct ?? "—"}%</p>
                <p>{uiStrings.pipeline.backtestForwardSource}: {candidate.backtest_vs_forward.baseline_provenance ?? uiStrings.pipeline.backtestForwardNoProvenance}</p>
              </div>
            ) : (
              <p className="text-xs text-text-muted">{uiStrings.pipeline.backtestForwardEmpty}</p>
            )}
          </CollapsibleContent>
        </Collapsible>
        <div className="flex gap-2">
          {canPromote && target !== null && (
            <Button
              size="sm"
              disabled={promote.isPending}
              onClick={() => promote.mutate(candidate.id)}
            >
              {interpolate(uiStrings.pipeline.promoteTo, { phase: target })}
            </Button>
          )}
          <Button size="sm" variant="destructive" onClick={() => setKillOpen(true)}>
            {uiStrings.pipeline.kill}
          </Button>
        </div>
      </CardContent>
      <KillDialog
        candidateId={candidate.id}
        botName={bot?.name ?? `#${candidate.bot_id}`}
        open={killOpen}
        onOpenChange={setKillOpen}
      />
    </Card>
  );
}
