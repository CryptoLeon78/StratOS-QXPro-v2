import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBots } from "@/hooks/queries/useBots";
import { usePortfolioCorrelations } from "@/hooks/queries/usePortfolio";
import { correlationHeatmapColor } from "@/lib/heatmap";
import { interpolate } from "@/lib/i18n";
import tokens from "@/styles/tokens";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.5: matriz de correlaciones P&L diario -- GET /portfolio/correlations
// solo trae bot_a_id/bot_b_id (sin nombre), se cruza con GET /bots para las
// etiquetas de fila/columna. Solo se incluyen los bots que aparecen en al
// menos un par (evita una matriz vacia enorme si la mayoria no tiene
// correlacion calculada todavia).
export function CorrelationMatrix() {
  const { data: correlations, isLoading } = usePortfolioCorrelations();
  const { data: bots } = useBots();

  const botNameById = new Map((bots ?? []).map((bot) => [bot.id, bot.name]));
  const botIds = Array.from(
    new Set((correlations ?? []).flatMap((row) => [row.bot_a_id, row.bot_b_id]))
  ).sort((a, b) => a - b);

  const cell = new Map<string, { correlation: number; redundant: boolean }>();
  for (const row of correlations ?? []) {
    cell.set(`${row.bot_a_id}-${row.bot_b_id}`, {
      correlation: row.correlation,
      redundant: row.is_redundant_pair,
    });
    cell.set(`${row.bot_b_id}-${row.bot_a_id}`, {
      correlation: row.correlation,
      redundant: row.is_redundant_pair,
    });
  }

  const mean =
    (correlations ?? []).length > 0
      ? (correlations ?? []).reduce((sum, row) => sum + row.correlation, 0) /
        (correlations ?? []).length
      : 0;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>{uiStrings.portfolio.correlationsTitle}</CardTitle>
        {!isLoading && (correlations ?? []).length > 0 && (
          <Badge variant="outline">
            {interpolate(uiStrings.portfolio.correlationsMedia, { value: mean.toFixed(2) })}
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        {!isLoading && botIds.length === 0 && (
          <p className="text-sm text-text-secondary">{uiStrings.portfolio.emptyState}</p>
        )}
        {botIds.length > 0 && (
          <div className="overflow-x-auto">
            <table className="text-xs">
              <thead>
                <tr>
                  <th className="sticky left-0 bg-bg-surface" />
                  {botIds.map((id) => (
                    <th key={id} className="max-w-16 px-1 pb-1 font-normal text-text-secondary">
                      <div className="truncate" title={botNameById.get(id) ?? `#${id}`}>
                        {botNameById.get(id) ?? `#${id}`}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {botIds.map((rowId) => (
                  <tr key={rowId}>
                    <th className="sticky left-0 whitespace-nowrap bg-bg-surface pr-2 text-left font-normal text-text-secondary">
                      {botNameById.get(rowId) ?? `#${rowId}`}
                    </th>
                    {botIds.map((colId) => {
                      if (rowId === colId) {
                        return (
                          <td
                            key={colId}
                            className="h-6 w-8 text-center"
                            style={{ backgroundColor: tokens.color.heatmap.diagonal, opacity: 0.5 }}
                          >
                            1.00
                          </td>
                        );
                      }
                      const value = cell.get(`${rowId}-${colId}`);
                      return (
                        <td
                          key={colId}
                          className="h-6 w-8 text-center text-text-primary"
                          style={{
                            backgroundColor: value
                              ? correlationHeatmapColor(value.correlation)
                              : tokens.color.bg.surfaceHover,
                            border: value?.redundant
                              ? `1px solid ${tokens.color.heatmap.redundantStroke}`
                              : undefined,
                          }}
                        >
                          {value ? value.correlation.toFixed(2) : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
