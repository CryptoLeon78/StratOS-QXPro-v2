import { useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EquityAreaChart } from "@/components/domain/EquityAreaChart";
import { useEquityCurve } from "@/hooks/queries/useEquityCurve";
import { useHeaderSummary } from "@/hooks/queries/useHeaderSummary";
import { computeMaxDrawdownPct } from "@/lib/equityStats";
import { formatAmount, formatPercent, formatSignedAmount } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import uiStrings from "@/styles/ui_strings.es.json";
import type { EquityRange } from "@/api/endpoints/header";

const RANGES: EquityRange[] = ["30d", "90d", "180d", "1y", "all"];

// PARTE 7.1: card "Equity del portfolio (todos los bots)" -- cifra grande,
// delta absoluto+%, "DD max. periodo" (calculado cliente, ver
// lib/equityStats.ts -- el backend no sirve DD por punto), selectores de
// rango, area verde (EquityAreaChart).
export function EquityCard() {
  const [range, setRange] = useState<EquityRange>("90d");
  const { data, isLoading } = useEquityCurve(range);
  // "equity sin snapshot reciente -> cifra atenuada + aviso" (PARTE 7.1,
  // caso limite): mismo data_stale_seconds que ya usa AppHeader para el
  // badge DATOS STALE, no una heuristica de frescura nueva/duplicada.
  const { data: header } = useHeaderSummary();
  const isStale = header?.data_stale_seconds !== null && header?.data_stale_seconds !== undefined;

  const points = (data ?? []).map((p) => ({ date: p.date, equity: Number(p.equity) }));
  const first = points.at(0)?.equity ?? 0;
  const last = points.at(-1)?.equity ?? 0;
  const delta = last - first;
  const deltaPct = first !== 0 ? (delta / first) * 100 : 0;
  const maxDdPct = computeMaxDrawdownPct(points.map((p) => p.equity));

  return (
    <Card data-testid="equity-card">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">{uiStrings.equityCard.title}</CardTitle>
        <div className="flex gap-1">
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
              {uiStrings.equityCard.ranges[r]}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-64" />
        ) : (
          <>
            <div className={cn("mb-1 flex items-baseline gap-3", isStale && "opacity-50")}>
              <span className="text-2xl font-semibold tabular-nums text-text-primary">
                {formatAmount(last)}
              </span>
              <span
                className={cn(
                  "text-sm font-medium tabular-nums",
                  delta < 0 ? "text-pnl-negative" : "text-pnl-positive"
                )}
              >
                {formatSignedAmount(delta)} ({deltaPct >= 0 ? "+" : ""}
                {formatPercent(deltaPct)})
              </span>
            </div>
            {isStale && (
              <p className="mb-2 text-xs text-semantic-warning">{uiStrings.equityCard.staleNotice}</p>
            )}
            <p className="mb-3 text-xs text-text-secondary">
              {interpolate(uiStrings.equityCard.maxDrawdownPeriod, {
                pct: formatPercent(maxDdPct),
              })}
            </p>
            <EquityAreaChart points={points} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
