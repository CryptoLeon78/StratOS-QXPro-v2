import { Bar, BarChart, CartesianGrid, ResponsiveContainer, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatSignedDelta } from "@/lib/formatters";
import { usePortfolioBlocks } from "@/hooks/queries/usePortfolio";
import tokens from "@/styles/tokens";
import uiStrings from "@/styles/ui_strings.es.json";

const BLOCK_LABELS = uiStrings.portfolio.blocks as Record<string, string>;

// PARTE 7.5: "Estructura macro 40/40/20" -- barras horizontales Objetivo
// vs Real por bloque (CONVEXO/CONCAVO/HIBRIDO, GET /portfolio/blocks) +
// tabla con Delta y nº de bots.
export function MacroStructureCard() {
  const { data, isLoading } = usePortfolioBlocks();

  const chartData = (data ?? []).map((row) => ({
    label: BLOCK_LABELS[row.key] ?? row.key,
    Objetivo: row.target_pct,
    Real: row.real_pct,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.portfolio.macroTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isLoading && (
          <ResponsiveContainer width="100%" height={140}>
            <BarChart layout="vertical" data={chartData} margin={{ left: 24 }}>
              <CartesianGrid horizontal={false} stroke={tokens.color.chart.grid} />
              <XAxis
                type="number"
                domain={[0, 60]}
                stroke={tokens.color.chart.axis}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={110}
                stroke={tokens.color.chart.axis}
                tick={{ fontSize: 11 }}
              />
              <Bar dataKey="Objetivo" fill={tokens.color.text.muted} radius={2} barSize={10} />
              <Bar dataKey="Real" fill={tokens.color.accent.primary} radius={2} barSize={10} />
            </BarChart>
          </ResponsiveContainer>
        )}
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-secondary">
              <th className="pb-1 font-normal">{uiStrings.portfolio.colBloque}</th>
              <th className="pb-1 font-normal">{uiStrings.portfolio.colObjetivo}</th>
              <th className="pb-1 font-normal">{uiStrings.portfolio.colReal}</th>
              <th className="pb-1 font-normal">{uiStrings.portfolio.colDelta}</th>
              <th className="pb-1 font-normal">{uiStrings.portfolio.colBots}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((row) => (
              <tr key={row.key} className="border-t border-border-subtle">
                <td className="py-1.5">{BLOCK_LABELS[row.key] ?? row.key}</td>
                <td className="py-1.5">{row.target_pct}%</td>
                <td className="py-1.5">{row.real_pct.toFixed(1)}%</td>
                <td
                  className={`py-1.5 ${row.delta_pct >= 0 ? "text-pnl-positive" : "text-pnl-negative"}`}
                >
                  {formatSignedDelta(row.delta_pct)}
                </td>
                <td className="py-1.5">{row.bot_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
