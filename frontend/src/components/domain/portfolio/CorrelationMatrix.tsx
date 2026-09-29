import type { CorrelationSource } from "@/api/endpoints/portfolio";
import { QueryError } from "@/components/domain/QueryError";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBots } from "@/hooks/queries/useBots";
import { useCorrelationCoverage, usePortfolioCorrelationSnapshot } from "@/hooks/queries/usePortfolio";
import { useAccountScope } from "@/hooks/useAccountScope";
import { correlationHeatmapColor } from "@/lib/heatmap";
import { interpolate } from "@/lib/i18n";
import tokens from "@/styles/tokens";
import uiStrings from "@/styles/ui_strings.es.json";

function SourceMatrix({ source }: { source: CorrelationSource }) {
  const { account } = useAccountScope();
  const { data: snapshot, isLoading, isError, refetch } = usePortfolioCorrelationSnapshot(source);
  const { data: coverage } = useCorrelationCoverage(source);
  const { data: bots } = useBots();
  const correlations = snapshot?.pairs ?? [];
  const botNameById = new Map((bots ?? []).map((bot) => [bot.id, bot.name]));
  const botIds = Array.from(new Set(correlations.flatMap((row) => [row.bot_a_id, row.bot_b_id]))).sort((a, b) => a - b);
  const cells = new Map<string, { correlation: number; redundant: boolean; lowConfidence: boolean }>();
  correlations.forEach((row) => {
    const value = { correlation: row.correlation, redundant: row.is_redundant_pair, lowConfidence: row.low_confidence };
    cells.set(`${row.bot_a_id}-${row.bot_b_id}`, value);
    cells.set(`${row.bot_b_id}-${row.bot_a_id}`, value);
  });
  const mean = correlations.length ? correlations.reduce((sum, row) => sum + row.correlation, 0) / correlations.length : 0;
  const anyLowConfidence = correlations.some((row) => row.low_confidence);
  const excluded = (coverage ?? []).filter((row) => !row.included);
  const installed = (coverage ?? []).length;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>{interpolate(uiStrings.portfolio.correlationSources[source], { account: account?.name ?? "" })}</CardTitle>
          <p className="text-xs text-text-secondary">{uiStrings.portfolio.correlationDailyNetPnl}</p>
          {snapshot && snapshot.status === "COMPLETED" && (
            <p className="text-xs text-text-muted">
              {interpolate(uiStrings.portfolio.correlationSnapshotMeta, {
                date: new Date(snapshot.created_at).toLocaleDateString("es-ES", { timeZone: "Europe/Madrid" }),
                days: snapshot.window_days,
                included: installed - excluded.length,
                installed,
              })}
            </p>
          )}
        </div>
        {!isLoading && correlations.length > 0 && <Badge variant="outline">{interpolate(uiStrings.portfolio.correlationsMedia, { value: mean.toFixed(2) })}</Badge>}
      </CardHeader>
      <CardContent className="space-y-3">
        {isError && <QueryError onRetry={() => void refetch()} />}
        {snapshot?.status === "WITHHELD" && <p className="text-sm text-text-secondary">{interpolate(uiStrings.portfolio.correlationWithheld, { reason: snapshot.reason ?? "—" })}</p>}
        {!isLoading && !isError && snapshot === null && <p className="text-sm text-text-secondary">{uiStrings.portfolio.correlationNoSnapshot}</p>}
        {botIds.length > 0 && <div className="overflow-x-auto"><table className="text-xs"><thead><tr><th className="sticky left-0 bg-bg-surface" />{botIds.map((id) => <th key={id} className="max-w-24 px-1 pb-1 font-normal text-text-secondary"><div className="truncate" title={botNameById.get(id) ?? `#${id}`}>{botNameById.get(id) ?? `#${id}`}</div></th>)}</tr></thead><tbody>{botIds.map((rowId) => <tr key={rowId}><th className="sticky left-0 whitespace-nowrap bg-bg-surface pr-2 text-left font-normal text-text-secondary">{botNameById.get(rowId) ?? `#${rowId}`}</th>{botIds.map((colId) => {
          if (rowId === colId) return <td key={colId} className="h-6 w-10 text-center" style={{ backgroundColor: tokens.color.heatmap.diagonal, opacity: 0.5 }}>1.00</td>;
          const value = cells.get(`${rowId}-${colId}`);
          return <td key={colId} className="h-6 w-10 text-center text-text-primary" style={{ backgroundColor: value ? correlationHeatmapColor(value.correlation) : tokens.color.bg.surfaceHover, border: value?.redundant ? `1px solid ${tokens.color.heatmap.redundantStroke}` : value?.lowConfidence ? "1px dashed currentColor" : undefined }}>{value ? value.correlation.toFixed(2) : "—"}</td>;
        })}</tr>)}</tbody></table></div>}
        {botIds.length > 0 && (
          <p className="text-xs text-text-muted">
            {uiStrings.portfolio.correlationRedundantLegend}
            {anyLowConfidence && ` ${uiStrings.portfolio.correlationLowConfidence}`}
          </p>
        )}
        {excluded.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-semibold text-text-secondary">{uiStrings.portfolio.coverageTitle}</h3>
            <ul className="space-y-0.5 text-xs">
              {excluded.map((row) => (
                <li key={row.bot_id} className="flex justify-between gap-3 text-text-secondary">
                  <span className="text-text-primary">{row.name}</span>
                  <span>
                    {row.reason ? uiStrings.portfolio.coverageReasons[row.reason] : ""}
                    {row.days !== null && row.trades !== null && ` · ${interpolate(uiStrings.portfolio.coverageActivity, { days: row.days, trades: row.trades })}`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function CorrelationMatrix() {
  // La captura contractual (`pestaña Portfolio.jpg`) muestra este titulo VISIBLE
  // sobre la matriz. Separarla en una tarjeta por procedencia esta cubierto por
  // el ADR de snapshots de correlacion, pero degradar el titulo a `aria-label`
  // no lo esta: se lee con lector de pantalla y desaparece de la pantalla.
  return <section className="space-y-3" aria-label={uiStrings.portfolio.correlationsTitle}>
    <h2 className="text-sm font-semibold text-text-primary">{uiStrings.portfolio.correlationsTitle}</h2>
    <div className="grid gap-4 xl:grid-cols-2">
      <SourceMatrix source="MT5_BACKTEST" />
      <SourceMatrix source="MT5_REAL" />
    </div>
  </section>;
}
