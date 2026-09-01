import { useState } from "react";

import { Button } from "@/components/ui/button";
import { CandidateCard } from "@/components/domain/pipeline/CandidateCard";
import { CreateCandidateDialog } from "@/components/domain/pipeline/CreateCandidateDialog";
import { usePipelineBoard } from "@/hooks/queries/usePipelineBoard";
import { useOperationalQueue } from "@/hooks/queries/useOperationalQueue";
import uiStrings from "@/styles/ui_strings.es.json";
import type { PipelinePhase } from "@/api/endpoints/pipeline";

type KanbanPhase = "F1" | "F2" | "F3" | "F4" | "F5" | "F6" | "F7";
const COLUMNS: KanbanPhase[] = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"];
const PAPER_PHASES = new Set<PipelinePhase>(["F1", "F2", "F3"]);

// PARTE 7.3: kanban de 7 columnas, zonas PAPER (F1-F3) / CAPITAL REAL
// (F4-F7) diferenciadas por color. Omitido (docs/backlog.md): tabla
// "Backtest vs Forward" (CandidateResponse no trae metricas de baseline/IS).
export default function PipelinePage() {
  const { data } = usePipelineBoard();
  const { data: operationalQueue } = useOperationalQueue();
  const [createOpen, setCreateOpen] = useState(false);

  const byPhase = new Map<string, typeof data>();
  for (const candidate of data ?? []) {
    const list = byPhase.get(candidate.current_phase) ?? [];
    list.push(candidate);
    byPhase.set(candidate.current_phase, list);
  }

  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">{uiStrings.pipeline.banner}</p>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          {uiStrings.pipeline.addCandidate}
        </Button>
      </div>
      <section className="rounded-lg border border-semantic-info/40 p-3 text-sm">
        <p className="font-semibold text-text-secondary">{uiStrings.pipeline.operationalQueueTitle}</p>
        {operationalQueue?.status === "READY" ? (
          <>
            <p className="mt-1 text-xs text-text-muted">
              {uiStrings.pipeline.operationalQueueReady.replace("{count}", String(operationalQueue.entries.length))}
            </p>
            {operationalQueue.entries.length === 0 ? (
              <p className="mt-1 text-xs text-text-muted">{uiStrings.pipeline.emptyColumn}</p>
            ) : (
              <ul className="mt-2 space-y-1 text-xs text-text-secondary">
                {operationalQueue.entries.map((entry) => (
                  <li key={entry.rank}>
                    #{entry.rank} · {entry.strategy_name} · {entry.symbol ?? "—"} {entry.timeframe ?? "—"} · {entry.state}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-xs text-text-muted">{uiStrings.pipeline.operationalQueueReadOnly}</p>
          </>
        ) : (
          <p className="mt-1 text-xs text-text-muted">
            {operationalQueue?.detail ?? uiStrings.pipeline.operationalQueueAbsent}
          </p>
        )}
      </section>
      <div className="grid grid-cols-1 gap-3 overflow-x-auto sm:grid-cols-2 lg:grid-flow-col lg:auto-cols-[260px]">
        {COLUMNS.map((phase) => {
          const candidates = byPhase.get(phase) ?? [];
          return (
            <div
              key={phase}
              className={`space-y-2 rounded-lg border p-2 ${
                PAPER_PHASES.has(phase)
                  ? "border-semantic-info/40"
                  : "border-semantic-success/40"
              }`}
            >
              <p className="px-1 text-xs font-semibold text-text-secondary">
                {uiStrings.pipeline.columns[phase]} ({candidates.length})
              </p>
              {candidates.length === 0 && (
                <p className="px-1 text-xs text-text-muted">{uiStrings.pipeline.emptyColumn}</p>
              )}
              {candidates.map((candidate) => (
                <CandidateCard key={candidate.id} candidate={candidate} />
              ))}
            </div>
          );
        })}
      </div>
      <p className="text-xs text-text-muted">{uiStrings.pipeline.manualPromoteOnly}</p>
      <CreateCandidateDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
