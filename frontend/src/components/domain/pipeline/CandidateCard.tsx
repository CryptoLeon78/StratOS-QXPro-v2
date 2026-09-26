import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { GateChecklist } from "@/components/domain/pipeline/GateChecklist";
import { DemoAttachmentDialog } from "@/components/domain/pipeline/DemoAttachmentDialog";
import { F4DemoInstallDialog } from "@/components/domain/pipeline/F4DemoInstallDialog";
import { KillDialog } from "@/components/domain/pipeline/KillDialog";
import { VerdictBadge } from "@/components/domain/VerdictBadge";
import { useBot } from "@/hooks/queries/useBots";
import { usePipelineActions } from "@/hooks/queries/usePipelineActions";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import {
  checkDemoReadiness,
  type DemoReadiness,
  type F5IncubationObservation,
  type PipelineCandidate,
  type PipelinePhase,
} from "@/api/endpoints/pipeline";

const MANUAL_PROMOTE_PHASES = new Set<PipelinePhase>(["F1", "F2"]);

function nextPhase(phase: PipelinePhase): number | null {
  const n = Number(phase.replace("F", ""));
  return Number.isFinite(n) ? n + 1 : null;
}

// PARTE 7.3: tarjeta de candidato del kanban. Boton "Promover" solo
// habilitado F1-F2. F3 exige evidencia de adjunto demo y F4+ solo puede
// avanzar por gate automatico -- el dropdown
// generico "Mover a..." de la captura se sustituye por los 2 botones
// reales (Promover/Matar), unicos que el backend soporta (ADR).
export function CandidateCard({
  candidate,
  incubationObservation,
}: {
  candidate: PipelineCandidate;
  incubationObservation?: F5IncubationObservation;
}) {
  const { data: bot } = useBot(candidate.bot_id);
  const { promote } = usePipelineActions();
  const [killOpen, setKillOpen] = useState(false);
  const [demoAttachmentOpen, setDemoAttachmentOpen] = useState(false);
  const [demoInstallOpen, setDemoInstallOpen] = useState(false);
  const [demoReadiness, setDemoReadiness] = useState<DemoReadiness | null>(null);
  const demoReadinessCheck = useMutation({
    mutationFn: () => checkDemoReadiness(candidate.id),
    onSuccess: setDemoReadiness,
  });
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
          {uiStrings.provenance[candidate.account_origin] ?? candidate.account_origin} ·{" "}
          {candidate.bot_origin}
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
        {candidate.current_phase === "F5" && (
          <Collapsible defaultOpen>
            <CollapsibleTrigger className="text-xs text-accent-primary">
              {uiStrings.pipeline.f5ObservationTitle}
            </CollapsibleTrigger>
            <CollapsibleContent>
              {incubationObservation ? (
                <div className="space-y-1 text-xs text-text-secondary">
                  <p className={incubationObservation.observation_status === "OBSERVED" ? "text-semantic-success" : "text-semantic-warning"}>
                    {incubationObservation.observation_status === "OBSERVED"
                      ? uiStrings.pipeline.f5Observed
                      : uiStrings.pipeline.f5Waiting}
                  </p>
                  <p>{interpolate(uiStrings.pipeline.f5Trades, { count: incubationObservation.demo_trade_count })}</p>
                  <p>{interpolate(uiStrings.pipeline.f5Days, { count: incubationObservation.valid_observation_days })}</p>
                  <p>{interpolate(uiStrings.pipeline.f5Reporter, { value: incubationObservation.ea_state?.ea_version ?? "—" })}</p>
                  <p>{interpolate(uiStrings.pipeline.f5Heartbeat, { value: incubationObservation.latest_heartbeat_at ?? "—" })}</p>
                  <p>{interpolate(uiStrings.pipeline.f5Equity, { value: incubationObservation.latest_equity?.equity ?? "—" })}</p>
                  {incubationObservation.tester_baseline ? (
                    <p>{uiStrings.pipeline.f5TesterBaseline}: PF {incubationObservation.tester_baseline.profit_factor.toFixed(2)} · Sharpe {incubationObservation.tester_baseline.sharpe.toFixed(2)}</p>
                  ) : <p className="text-text-muted">{uiStrings.pipeline.f5NoBaseline}</p>}
                  {incubationObservation.missing_evidence.length > 0 && (
                    <p className="text-text-muted">{interpolate(uiStrings.pipeline.f5Missing, { items: incubationObservation.missing_evidence.join(", ") })}</p>
                  )}
                </div>
              ) : <p className="text-xs text-text-muted">{uiStrings.pipeline.f5NoTelemetry}</p>}
            </CollapsibleContent>
          </Collapsible>
        )}
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
          {candidate.current_phase === "F3" && (
            <>
              <Button size="sm" onClick={() => setDemoAttachmentOpen(true)}>
                {uiStrings.pipeline.registerDemoAttachment}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={demoReadinessCheck.isPending}
                onClick={() => demoReadinessCheck.mutate()}
              >
                {uiStrings.pipeline.checkDemoReadiness}
              </Button>
            </>
          )}
          {candidate.current_phase === "F4" && candidate.verdict === "GO" && (
            <Button size="sm" onClick={() => setDemoInstallOpen(true)}>{uiStrings.pipeline.f4InstallConfirm}</Button>
          )}
          <Button size="sm" variant="destructive" onClick={() => setKillOpen(true)}>
            {uiStrings.pipeline.kill}
          </Button>
        </div>
        {demoReadiness && (
          <div className="space-y-1 rounded-md border border-semantic-warning/40 p-2 text-xs text-text-secondary">
            {demoReadiness.requirements.map((requirement) => (
              <p key={requirement.key}>
                {requirement.satisfied
                  ? uiStrings.pipeline.demoReadinessPassMark
                  : uiStrings.pipeline.demoReadinessFailMark}{" "}
                {uiStrings.pipeline.demoReadiness[requirement.key as keyof typeof uiStrings.pipeline.demoReadiness]}
              </p>
            ))}
            <p className="text-text-muted">{uiStrings.pipeline.demoReadinessNext}</p>
          </div>
        )}
      </CardContent>
      <KillDialog
        candidateId={candidate.id}
        botName={bot?.name ?? `#${candidate.bot_id}`}
        open={killOpen}
        onOpenChange={setKillOpen}
      />
      <DemoAttachmentDialog
        candidateId={candidate.id}
        open={demoAttachmentOpen}
        onOpenChange={setDemoAttachmentOpen}
        onRegistered={setDemoReadiness}
      />
      <F4DemoInstallDialog candidateId={candidate.id} open={demoInstallOpen} onOpenChange={setDemoInstallOpen} />
    </Card>
  );
}
