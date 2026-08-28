import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useUmsMonthlyHistory } from "@/hooks/queries/useScaling";
import { formatAmount, formatPercent, formatSignedDelta } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.9 "Evolucion mensual": GET /scaling/monthly. `metrics` es JSON
// libre; desde G10 (services/ums.py::monthly_evolution_metrics()) trae
// ademas {trades, retorno_pct, max_dd_pct} del ultimo mes (trades
// cerrados reales + curva de equity real de portfolio) -- solo cuando la
// fila corresponde a un evento de ascenso/bajada real (confirm_advance/
// check_automatic_downgrade la invocan), no en cada fila historica. Sin
// equity suficiente en la ventana, retorno_pct/max_dd_pct quedan `null`,
// nunca se inventan.
function numOrNull(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

export function MonthlyEvolutionTable() {
  const { data } = useUmsMonthlyHistory();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.escalado.monthlyEvolutionTitle}</CardTitle>
      </CardHeader>
      <CardContent>
        {(data ?? []).length === 0 && (
          <p className="text-sm text-text-secondary">{uiStrings.escalado.emptyMonthly}</p>
        )}
        {(data ?? []).length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-secondary">
                <th className="pb-1 font-normal">{uiStrings.escalado.colMes}</th>
                <th className="pb-1 font-normal">{uiStrings.escalado.colEquity}</th>
                <th className="pb-1 font-normal">{uiStrings.escalado.colTrades}</th>
                <th className="pb-1 font-normal">{uiStrings.escalado.colRetorno}</th>
                <th className="pb-1 font-normal">{uiStrings.escalado.colMaxDd}</th>
                <th className="pb-1 font-normal">{uiStrings.escalado.colSharpe}</th>
                <th className="pb-1 font-normal">{uiStrings.escalado.colFase}</th>
              </tr>
            </thead>
            <tbody>
              {[...(data ?? [])].reverse().map((row) => {
                const trades = numOrNull(row.metrics.trades);
                const retorno = numOrNull(row.metrics.retorno_pct);
                const maxDd = numOrNull(row.metrics.max_dd_pct);
                return (
                  <tr key={row.id} className="border-t border-border-subtle">
                    <td className="py-1.5 text-text-primary">
                      {new Date(row.ts).toLocaleDateString("es-ES", {
                        year: "numeric",
                        month: "2-digit",
                      })}
                    </td>
                    <td className="py-1.5 text-text-secondary">{formatAmount(row.equity_at)}</td>
                    <td className="py-1.5 text-text-secondary">{trades ?? "—"}</td>
                    <td
                      className={cn(
                        "py-1.5",
                        retorno === null
                          ? "text-text-secondary"
                          : retorno >= 0
                            ? "text-pnl-positive"
                            : "text-pnl-negative"
                      )}
                    >
                      {retorno === null ? "—" : formatSignedDelta(retorno)}
                    </td>
                    <td className="py-1.5 text-text-secondary">
                      {maxDd === null ? "—" : formatPercent(maxDd)}
                    </td>
                    <td className="py-1.5 text-text-secondary">
                      {typeof row.metrics.sharpe === "number" ? row.metrics.sharpe.toFixed(2) : "—"}
                    </td>
                    <td className="py-1.5 text-text-secondary">F{row.phase}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}
