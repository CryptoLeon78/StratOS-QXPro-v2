import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useUmsPhasesConfig } from "@/hooks/queries/useConfig";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.9 "Las 6 fases UMS": tabla estatica de referencia, GET
// /config/ums-phases (nuevo en G7).
export function PhasesTable() {
  const { data } = useUmsPhasesConfig();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.escalado.phasesTableTitle}</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-secondary">
              <th className="pb-1 font-normal">{uiStrings.escalado.colFase}</th>
              <th className="pb-1 font-normal">{uiStrings.escalado.colEquity}</th>
              <th className="pb-1 font-normal">{uiStrings.escalado.colRiesgoOp}</th>
              <th className="pb-1 font-normal">{uiStrings.escalado.colKelly}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((phase) => (
              <tr key={phase.phase} className="border-t border-border-subtle">
                <td className="py-1.5 text-text-primary">
                  {phase.phase} · {phase.name}
                </td>
                <td className="py-1.5 text-text-secondary">
                  {phase.equity_min}–{phase.equity_max ?? "∞"}
                </td>
                <td className="py-1.5 text-text-secondary">
                  {phase.risk_per_trade_pct_min && phase.risk_per_trade_pct_max
                    ? `${phase.risk_per_trade_pct_min}-${phase.risk_per_trade_pct_max}%`
                    : (phase.risk_note ?? "—")}
                </td>
                <td className="py-1.5 text-text-secondary">K {phase.kelly_fraction}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
