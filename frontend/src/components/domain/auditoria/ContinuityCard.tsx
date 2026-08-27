import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useHeartbeat } from "@/hooks/queries/useExecution";
import { formatPercent } from "@/lib/formatters";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.9 "Continuidad del envio (7 dias)": reutiliza `uptime_pct_7d` de
// GET /execution/heartbeat (cross-tab con Ejecucion, mismo dato real).
// "Tramos sin envio" detallados de la captura no estan en ningun schema
// (solo el % agregado) -- omitido, docs/backlog.md.
export function ContinuityCard() {
  const { data } = useHeartbeat();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.auditoria.continuityTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {(data ?? []).map((row) => (
          <div key={row.account_id} className="flex items-center justify-between text-sm">
            <span className="text-text-secondary">Cuenta #{row.account_id}</span>
            <span className="font-semibold text-text-primary">{formatPercent(row.uptime_pct_7d)}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
