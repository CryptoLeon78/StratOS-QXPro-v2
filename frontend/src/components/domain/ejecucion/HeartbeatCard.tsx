import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useHeartbeat } from "@/hooks/queries/useExecution";
import { formatPercent } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.10 "Heartbeat": GET /execution/heartbeat, una fila por cuenta.
// `connected` ya viene calculado por el backend (gap real vs
// heartbeat_gap_threshold_s), no se recalcula en frontend.
export function HeartbeatCard() {
  const { data } = useHeartbeat();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.ejecucion.heartbeatTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {(data ?? []).map((row) => (
          <div key={row.account_id}>
            <p
              className={
                row.connected ? "font-semibold text-semantic-success" : "font-semibold text-semantic-danger"
              }
            >
              {row.connected ? uiStrings.ejecucion.terminalReporting : uiStrings.ejecucion.terminalDown}
            </p>
            <p className="text-xs text-text-secondary">
              {row.last_ts &&
                interpolate(uiStrings.ejecucion.lastReport, {
                  date: new Date(row.last_ts).toLocaleString("es-ES", { timeZone: "Europe/Madrid" }),
                })}
            </p>
            <p className="text-xs text-text-secondary">
              {interpolate(uiStrings.ejecucion.uptime7d, { pct: formatPercent(row.uptime_pct_7d) })}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
