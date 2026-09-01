import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import uiStrings from "@/styles/ui_strings.es.json";
import { useTca } from "@/hooks/queries/useExecution";

// PARTE 7.10/7.2: se activa exclusivamente con telemetría v1.1 recibida;
// sin reporter no se inventa ni un fill, ni spread, ni rechazo.
export function TcaPendingCard() {
  const { data: tca } = useTca();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.ejecucion.tcaTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {tca ? (
          <>
            <p className="text-sm text-text-secondary">
              {uiStrings.ejecucion.tcaFills}: {tca.fills} · P50 {tca.slippage_p50 ?? "—"} · P95 {tca.slippage_p95 ?? "—"} · P99 {tca.slippage_p99 ?? "—"} · Asymmetry {tca.asymmetry_index?.toFixed(2) ?? "—"} · IS P50 {tca.implementation_shortfall_p50 ?? "—"} · {uiStrings.ejecucion.rejectedOrders}: {tca.rejected_orders}
            </p>
            {tca.broker_profiles.map((profile) => (
              <p key={`${profile.broker}-${profile.symbol}`} className="text-xs text-text-muted">
                {uiStrings.ejecucion.brokerProfile}: {profile.broker} · {profile.symbol} · {uiStrings.ejecucion.tcaFills} {profile.fills} · {uiStrings.ejecucion.spreadP50} {profile.spread_p50 ?? "—"}
              </p>
            ))}
          </>
        ) : (
          <>
            <p className="text-sm text-text-secondary">{uiStrings.ejecucion.tcaPending}</p>
            <p className="text-xs text-text-muted">{uiStrings.ejecucion.tcaPendingDetail}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
