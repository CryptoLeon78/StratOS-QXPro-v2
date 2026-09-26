import { useQuery } from "@tanstack/react-query";

import { getF5Incubation } from "@/api/endpoints/pipeline";
import { AccountCard } from "@/components/domain/cuentas-ea/AccountCard";
import { CandidateCard } from "@/components/domain/pipeline/CandidateCard";
import { ProvenanceBadge } from "@/components/domain/ProvenanceBadge";
import { useAccounts } from "@/hooks/queries/useAccounts";
import { useBots } from "@/hooks/queries/useBots";
import { usePipelineBoard } from "@/hooks/queries/usePipelineBoard";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

type IncubatorLane = "F4" | "F5" | "F6";

const INCUBATOR_LANES: Array<{ phase: IncubatorLane; title: string; detail: string }> = [
  {
    phase: "F4",
    title: uiStrings.pipeline.incubatorInstallTitle,
    detail: uiStrings.pipeline.incubatorInstallDetail,
  },
  {
    phase: "F5",
    title: uiStrings.pipeline.incubatorObserveTitle,
    detail: uiStrings.pipeline.incubatorObserveDetail,
  },
  {
    phase: "F6",
    title: uiStrings.pipeline.incubatorDecisionTitle,
    detail: uiStrings.pipeline.incubatorDecisionDetail,
  },
];

// Pipeline no es una cantera de investigación. La admisión previa queda fuera
// de esta superficie; aquí sólo se gobierna Incubadora y se observan cuentas
// reales. Ningún componente puede despachar acciones a BEPB o JJTI.
export default function PipelinePage() {
  const { data: candidates } = usePipelineBoard();
  const { data: observations } = useQuery({
    queryKey: ["f5-incubation"],
    queryFn: getF5Incubation,
    refetchInterval: 5_000,
  });
  const { data: accounts } = useAccounts();
  const { data: bots } = useBots();

  const observationByCandidateId = new Map(
    (observations ?? []).map((observation) => [observation.candidate_id, observation])
  );
  const candidatesByPhase = new Map<IncubatorLane, NonNullable<typeof candidates>>();
  for (const candidate of candidates ?? []) {
    if (candidate.current_phase === "F4" || candidate.current_phase === "F5" || candidate.current_phase === "F6") {
      const lane = candidatesByPhase.get(candidate.current_phase) ?? [];
      lane.push(candidate);
      candidatesByPhase.set(candidate.current_phase, lane);
    }
  }
  const realAccounts = (accounts ?? []).filter((account) => account.data_origin === "BROKER_REAL");
  const realAccountIds = new Set(realAccounts.map((account) => account.id));
  const accountNameById = new Map(realAccounts.map((account) => [account.id, account.name]));
  const portfolioBots = (bots ?? []).filter((bot) => realAccountIds.has(bot.account_id));

  return (
    <div className="space-y-4 p-4">
      <div className="space-y-2">
        <p className="text-sm text-text-secondary">{uiStrings.pipeline.operationalBanner}</p>
        <p className="text-xs text-text-muted">{uiStrings.pipeline.operationalBoundary}</p>
        <ProvenanceBadge />
      </div>

      <section aria-labelledby="incubator-board-title" className="space-y-2">
        <h2 id="incubator-board-title" className="text-sm font-semibold text-text-primary">
          {uiStrings.pipeline.incubatorBoardTitle}
        </h2>
        <div className="grid grid-cols-1 items-start gap-3 overflow-x-auto md:grid-cols-3 md:auto-cols-[minmax(260px,1fr)]">
          {INCUBATOR_LANES.map((lane) => {
            const laneCandidates = candidatesByPhase.get(lane.phase) ?? [];
            const showsPortfolioBots = lane.phase === "F6";
            return (
              <div key={lane.phase} className="space-y-2 rounded-lg border border-semantic-warning/40 p-2">
                <div className="px-1">
                  <p className="text-xs font-semibold text-text-secondary">
                    {lane.title} ({laneCandidates.length})
                  </p>
                  <p className="mt-1 text-xs text-text-muted">{lane.detail}</p>
                </div>
                {showsPortfolioBots && (
                  <div className="space-y-1 border-t border-border-subtle px-1 pt-2">
                    <p className="text-xs font-semibold text-text-secondary">
                      {interpolate(uiStrings.pipeline.portfolioBotsTitle, { count: portfolioBots.length })}
                    </p>
                    {portfolioBots.length === 0 ? (
                      <p className="text-xs text-text-muted">{uiStrings.pipeline.portfolioBotsEmpty}</p>
                    ) : (
                      <ul className="space-y-1">
                        {portfolioBots.map((bot) => (
                          <li key={bot.id} className="rounded-md border border-border-subtle p-2 text-xs">
                            <p className="font-semibold text-text-primary">{bot.name}</p>
                            <p className="mt-1 text-text-secondary">
                              {interpolate(uiStrings.pipeline.portfolioBotIdentity, {
                                account: accountNameById.get(bot.account_id) ?? "—",
                                magic: bot.magic_number,
                                market: bot.market,
                                timeframe: bot.timeframe,
                              })}
                            </p>
                            <p className="mt-1 text-text-muted">
                              {interpolate(uiStrings.pipeline.portfolioBotState, {
                                role: bot.role,
                                state: bot.semaphore_state,
                              })}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                {laneCandidates.length === 0 && !showsPortfolioBots ? (
                  <p className="px-1 text-xs text-text-muted">{uiStrings.pipeline.emptyColumn}</p>
                ) : laneCandidates.length > 0 ? (
                  laneCandidates.map((candidate) => (
                    <CandidateCard
                      key={candidate.id}
                      candidate={candidate}
                      incubationObservation={observationByCandidateId.get(candidate.id)}
                    />
                  ))) : null}
              </div>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="real-portfolios-title" className="space-y-2">
        <div>
          <h2 id="real-portfolios-title" className="text-sm font-semibold text-text-primary">
            {uiStrings.pipeline.realPortfoliosTitle}
          </h2>
          <p className="mt-1 text-xs text-text-muted">{uiStrings.pipeline.realPortfoliosDetail}</p>
        </div>
        {realAccounts.length === 0 ? (
          <p className="text-sm text-text-secondary">{uiStrings.pipeline.realPortfoliosEmpty}</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {realAccounts.map((account) => (
              <AccountCard key={account.id} account={account} bots={bots ?? []} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
