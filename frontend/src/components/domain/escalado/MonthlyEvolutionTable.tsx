import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useUmsMonthlyHistory } from "@/hooks/queries/useScaling";
import { formatAmount } from "@/lib/formatters";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.9 "Evolucion mensual": GET /scaling/monthly. Verificado leyendo
// services/ums.py -- `metrics` solo popula {sharpe, dd_pct} en un ascenso
// confirmado (confirm_advance) y queda vacio {} en una bajada automatica
// (check_automatic_downgrade); nunca trae trades/retorno/max_dd. Se
// omiten esas 3 columnas de la captura (docs/backlog.md), Sharpe se
// muestra solo cuando el JSON libre lo trae.
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
                <th className="pb-1 font-normal">{uiStrings.escalado.colSharpe}</th>
                <th className="pb-1 font-normal">{uiStrings.escalado.colFase}</th>
              </tr>
            </thead>
            <tbody>
              {[...(data ?? [])].reverse().map((row) => (
                <tr key={row.id} className="border-t border-border-subtle">
                  <td className="py-1.5 text-text-primary">
                    {new Date(row.ts).toLocaleDateString("es-ES", { year: "numeric", month: "2-digit" })}
                  </td>
                  <td className="py-1.5 text-text-secondary">{formatAmount(row.equity_at)}</td>
                  <td className="py-1.5 text-text-secondary">
                    {typeof row.metrics.sharpe === "number" ? row.metrics.sharpe.toFixed(2) : "—"}
                  </td>
                  <td className="py-1.5 text-text-secondary">F{row.phase}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}
