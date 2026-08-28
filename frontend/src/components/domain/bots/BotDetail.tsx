import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BotPnlChart } from "@/components/domain/bots/BotPnlChart";
import { ImpulseFormDialog } from "@/components/domain/bots/ImpulseFormDialog";
import { RMultipleHistogram } from "@/components/domain/bots/RMultipleHistogram";
import { SemaphoreBadge } from "@/components/domain/SemaphoreBadge";
import {
  useBotMetrics,
  useBotOpenPositions,
  useBotPnlCurve,
  useBotRMultiples,
  useBotSemaphoreHistory,
} from "@/hooks/queries/useBots";
import { useSemaphoreInstructions } from "@/hooks/queries/useConfig";
import { formatAmount, formatPercent } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { BotRow } from "@/api/endpoints/bots";

const RANGES = ["30d", "90d", "180d", "all"] as const;

function instructionFor(
  state: string,
  magicNumber: number,
  instructions: { verde: string; amarillo: string; naranja_template: string } | undefined
): string | null {
  if (!instructions) return null;
  if (state === "VERDE") return instructions.verde;
  if (state === "AMARILLO") return instructions.amarillo;
  if (state === "NARANJA") return interpolate(instructions.naranja_template, { magic: magicNumber });
  return null;
}

function fmtNum(value: number | null, digits = 2): string {
  return value === null ? "—" : value.toFixed(digits);
}

// PARTE 7.4, panel de detalle. Metricas completas/Contribucion/
// Posiciones abiertas/Histograma de retornos/P&L acumulado (G10, grupo m):
// consumen GET /bots/{id}/metrics + /pnl-curve + /r-multiples +
// /open-positions (backend construido en G10, commit f2d8d2f). "Historial
// del pipeline" sigue sustituido por "Historial de semaforo" (ADR 0003,
// G7) -- dato real disponible en el mismo lugar del layout. "TRADES/SEM"
// de la captura se muestra como "Trades/mes" (ADR 0008): el backend
// calcula mensual, convertir a semanal duplicaria una constante de diseno
// (4.345) sin hogar declarado.
export function BotDetail({ bot }: { bot: BotRow }) {
  const [impulseOpen, setImpulseOpen] = useState(false);
  const [range, setRange] = useState<(typeof RANGES)[number]>("90d");
  const { data: instructions } = useSemaphoreInstructions();
  const { data: semaphoreHistory } = useBotSemaphoreHistory(bot.id);
  const { data: metrics } = useBotMetrics(bot.id);
  const { data: pnlCurve } = useBotPnlCurve(bot.id);
  const { data: rMultiples } = useBotRMultiples(bot.id);
  const { data: openPositions } = useBotOpenPositions(bot.id);
  const instructionText = instructionFor(bot.semaphore_state, bot.magic_number, instructions);
  const tradeCount = (pnlCurve ?? []).filter((p) => p.ts !== null).length;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div>
            <CardTitle>{bot.name}</CardTitle>
            <p className="text-xs text-text-secondary">
              magic {bot.magic_number} · {bot.market} {bot.timeframe} · {bot.profile.toLowerCase()}{" "}
              · {bot.pipeline_phase} · {bot.role.toLowerCase()}
            </p>
          </div>
          <SemaphoreBadge state={bot.semaphore_state} />
        </CardHeader>
        <CardContent className="space-y-3">
          {instructionText && <p className="text-sm text-text-secondary">{instructionText}</p>}
          <div className="flex flex-wrap items-center gap-2">
            {RANGES.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRange(r)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                  r === range
                    ? "bg-accent-primary text-text-primary"
                    : "text-text-secondary hover:bg-bg-surfaceHover"
                )}
              >
                {uiStrings.bots.ranges[r]}
              </button>
            ))}
            <Button variant="outline" size="sm" onClick={() => setImpulseOpen(true)}>
              {uiStrings.bots.impulseButton}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{interpolate(uiStrings.bots.pnlChartTitle, { count: tradeCount })}</CardTitle>
        </CardHeader>
        <CardContent>
          <BotPnlChart points={pnlCurve ?? []} range={range} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.rollingVsBaselineTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            {!metrics?.has_baseline ? (
              <p className="text-sm text-text-secondary">{uiStrings.bots.noBaselineYet}</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-secondary">
                    <th className="pb-1 font-normal" />
                    <th className="pb-1 font-normal">{uiStrings.bots.colRolling}</th>
                    <th className="pb-1 font-normal">{uiStrings.bots.colBaseline}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-border-subtle">
                    <td className="py-1.5">{uiStrings.bots.rowSharpeVsBaseline}</td>
                    <td className="py-1.5">{fmtNum(metrics.sharpe_rolling)}</td>
                    <td className="py-1.5 text-text-secondary">{fmtNum(metrics.sharpe_baseline)}</td>
                  </tr>
                  <tr className="border-t border-border-subtle">
                    <td className="py-1.5">{uiStrings.bots.rowExpectancy}</td>
                    <td className="py-1.5">{fmtNum(metrics.exp_rolling)}</td>
                    <td className="py-1.5 text-text-secondary">{fmtNum(metrics.exp_baseline)}</td>
                  </tr>
                  <tr className="border-t border-border-subtle">
                    <td className="py-1.5">{uiStrings.bots.rowWinRateDrift}</td>
                    <td className="py-1.5">
                      {metrics.win_rate_rolling === null ? "—" : formatPercent(metrics.win_rate_rolling * 100)}
                    </td>
                    <td className="py-1.5 text-text-secondary">
                      {metrics.win_rate_baseline === null ? "—" : formatPercent(metrics.win_rate_baseline * 100)}
                    </td>
                  </tr>
                  <tr className="border-t border-border-subtle">
                    <td className="py-1.5">{uiStrings.bots.rowPayoff}</td>
                    <td className="py-1.5">{fmtNum(metrics.payoff_rolling)}</td>
                    <td className="py-1.5 text-text-secondary">{fmtNum(metrics.payoff_baseline)}</td>
                  </tr>
                  <tr className="border-t border-border-subtle">
                    <td className="py-1.5">{uiStrings.bots.rowDurationTrade}</td>
                    <td className="py-1.5">{fmtNum(metrics.avg_trade_duration_rolling_min, 0)}</td>
                    <td className="py-1.5 text-text-secondary">
                      {fmtNum(metrics.avg_trade_duration_baseline_min, 0)}
                    </td>
                  </tr>
                  <tr className="border-t border-border-subtle">
                    <td className="py-1.5">{uiStrings.bots.rowLossStreak}</td>
                    <td className="py-1.5">{metrics.loss_streak ?? "—"}</td>
                    <td className="py-1.5 text-text-secondary">{metrics.loss_streak_baseline ?? "—"}</td>
                  </tr>
                  <tr className="border-t border-border-subtle">
                    <td className="py-1.5">{uiStrings.bots.rowDdRolling}</td>
                    <td className="py-1.5">
                      {metrics.dd_rolling_pct === null ? "—" : formatPercent(metrics.dd_rolling_pct)}
                    </td>
                    <td className="py-1.5 text-text-secondary">
                      {metrics.dd_contract_pct === null ? "—" : formatPercent(metrics.dd_contract_pct)}
                    </td>
                  </tr>
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.completeMetricsTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            {metrics && (
              <dl className="grid grid-cols-3 gap-x-3 gap-y-3 text-xs">
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colProfitFactor}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.pf_rolling)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colExpectancyR}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.exp_rolling)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colSharpe}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.sharpe_rolling)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colSortino}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.sortino)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colCalmar}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.calmar)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colMaxDd}</dt>
                  <dd className="text-text-primary">{formatPercent(metrics.max_dd_pct)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colDdActual}</dt>
                  <dd className="text-text-primary">
                    {metrics.dd_rolling_pct === null ? "—" : formatPercent(metrics.dd_rolling_pct)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colRecoveryF}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.recovery_factor)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colUlcer}</dt>
                  <dd className="text-text-primary">{metrics.ulcer_index.toFixed(3)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colWinRate}</dt>
                  <dd className="text-text-primary">
                    {metrics.win_rate_rolling === null ? "—" : formatPercent(metrics.win_rate_rolling * 100)}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colPayoff}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.payoff_rolling)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colMcl}</dt>
                  <dd className="text-text-primary">{metrics.loss_streak ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colDurMedia}</dt>
                  <dd className="text-text-primary">{fmtNum(metrics.avg_trade_duration_rolling_min, 0)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colTradesPerMonth}</dt>
                  <dd className="text-text-primary">{metrics.trades_per_month.toFixed(1)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">{uiStrings.bots.colPnlNeto}</dt>
                  <dd className="text-text-primary">{formatAmount(metrics.net_pnl)}</dd>
                </div>
              </dl>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.contributionTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-3 text-xs">
              <div>
                <dt className="text-text-secondary">{uiStrings.bots.colPctOfTotalPnl}</dt>
                <dd className="text-text-primary">
                  {metrics?.pct_of_total_pnl === null || metrics?.pct_of_total_pnl === undefined
                    ? "—"
                    : formatPercent(metrics.pct_of_total_pnl)}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.bots.colCorrelationVsRest}</dt>
                <dd className="text-text-primary">{fmtNum(metrics?.correlation_vs_rest ?? null)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.bots.sizingObjetivo}</dt>
                <dd className="text-text-primary">{bot.capital_allocated_pct}%</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.bots.colPnlBotAccount}</dt>
                <dd className="text-text-primary">
                  {metrics ? `${formatAmount(metrics.pnl_bot)} / ${formatAmount(metrics.pnl_account)}` : "—"}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>
              {interpolate(uiStrings.bots.openPositionsTitle, {
                count: (openPositions ?? []).length,
              })}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(openPositions ?? []).length === 0 ? (
              <p className="text-sm text-text-secondary">{uiStrings.bots.emptyOpenPositions}</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-text-secondary">
                    <th className="pb-1 font-normal">{uiStrings.bots.colSymbol}</th>
                    <th className="pb-1 font-normal">{uiStrings.bots.colType}</th>
                    <th className="pb-1 font-normal">{uiStrings.bots.colVolume}</th>
                    <th className="pb-1 font-normal">{uiStrings.bots.colProfit}</th>
                  </tr>
                </thead>
                <tbody>
                  {(openPositions ?? []).map((pos) => (
                    <tr key={pos.id} className="border-t border-border-subtle">
                      <td className="py-1.5">{pos.symbol}</td>
                      <td className="py-1.5">{pos.type}</td>
                      <td className="py-1.5">{pos.volume}</td>
                      <td
                        className={cn(
                          "py-1.5",
                          Number(pos.profit) >= 0 ? "text-pnl-positive" : "text-pnl-negative"
                        )}
                      >
                        {formatAmount(pos.profit)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.histogramTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            {(rMultiples ?? []).length === 0 ? (
              <p className="text-sm text-text-secondary">{uiStrings.bots.emptyHistogram}</p>
            ) : (
              <RMultipleHistogram values={rMultiples ?? []} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.semaphoreHistoryTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            {(semaphoreHistory ?? []).length === 0 && (
              <p className="text-sm text-text-secondary">
                {uiStrings.bots.emptySemaphoreHistory}
              </p>
            )}
            <ul className="space-y-2">
              {(semaphoreHistory ?? []).map((entry) => (
                <li key={entry.id} className="text-xs">
                  <span className="text-text-secondary">
                    {new Date(entry.ts).toLocaleDateString("es-ES")}
                  </span>{" "}
                  <Badge variant="outline">{entry.from_state}</Badge> →{" "}
                  <Badge variant="outline">{entry.to_state}</Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <ImpulseFormDialog
        botId={bot.id}
        botName={bot.name}
        open={impulseOpen}
        onOpenChange={setImpulseOpen}
      />
    </div>
  );
}
