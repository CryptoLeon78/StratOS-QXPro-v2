import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatSignedDelta } from "@/lib/formatters";
import { usePortfolioProfiles } from "@/hooks/queries/usePortfolio";
import uiStrings from "@/styles/ui_strings.es.json";

const PROFILE_LABELS = uiStrings.portfolio.profiles as Record<string, string>;

// La API modela GRID y SCALPING como 2 perfiles independientes
// (PROFILE_TARGET en core/routers/portfolio.py: 5%+5%), pero la captura
// muestra una unica fila "Grid / Scalping" (10%) -- se fusionan aqui para
// fidelidad visual (ADR: portfolio-grid-scalping-fusionados), sumando
// target/real/bots de ambas filas reales.
function mergeGridScalping(
  rows: { key: string; target_pct: number; real_pct: number; delta_pct: number; bot_count: number }[]
) {
  const gridScalping = rows.filter((r) => r.key === "GRID" || r.key === "SCALPING");
  const rest = rows.filter((r) => r.key !== "GRID" && r.key !== "SCALPING");
  if (gridScalping.length === 0) return rest;
  const merged = {
    key: "GRID_SCALPING",
    target_pct: gridScalping.reduce((sum, r) => sum + r.target_pct, 0),
    real_pct: gridScalping.reduce((sum, r) => sum + r.real_pct, 0),
    delta_pct: gridScalping.reduce((sum, r) => sum + r.delta_pct, 0),
    bot_count: gridScalping.reduce((sum, r) => sum + r.bot_count, 0),
  };
  return [...rest, merged];
}

export function MicroProfilesTable() {
  const { data } = usePortfolioProfiles();
  const rows = mergeGridScalping(data ?? []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.portfolio.microTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
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
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-border-subtle">
                <td className="py-1.5">{PROFILE_LABELS[row.key] ?? row.key}</td>
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
        <p className="text-xs text-text-muted">{uiStrings.portfolio.microFootnote}</p>
      </CardContent>
    </Card>
  );
}
