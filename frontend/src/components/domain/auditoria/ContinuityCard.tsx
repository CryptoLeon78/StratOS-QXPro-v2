import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useContinuityGaps } from "@/hooks/queries/useAudit";
import { useHeartbeat } from "@/hooks/queries/useExecution";
import { formatPercent } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// PARTE 7.9 "Continuidad del envio (7 dias)": reutiliza `uptime_pct_7d` de
// GET /execution/heartbeat (cross-tab con Ejecucion, mismo dato real) +
// "Tramos sin envio" detallados (G10, GET /audit/continuity-gaps) --
// `compute_send_continuity()` ya calculaba `gaps` con detalle por tramo
// desde G5, solo faltaba exponerlo.
export function ContinuityCard() {
  const { data } = useHeartbeat();
  const { data: continuityGaps } = useContinuityGaps();
  const gapsByAccount = new Map((continuityGaps ?? []).map((c) => [c.account_id, c.gaps]));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.auditoria.continuityTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {(data ?? []).map((row) => {
          const gaps = gapsByAccount.get(row.account_id) ?? [];
          return (
            <div key={row.account_id} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">Cuenta #{row.account_id}</span>
                <span className="font-semibold text-text-primary">
                  {formatPercent(row.uptime_pct_7d)}
                </span>
              </div>
              <div>
                <p className="text-xs font-medium text-text-secondary">
                  {interpolate(uiStrings.auditoria.continuityGapsTitle, { count: gaps.length })}
                </p>
                {gaps.length === 0 ? (
                  <p className="text-xs text-text-muted">{uiStrings.auditoria.continuityGapsEmpty}</p>
                ) : (
                  <ul className="space-y-0.5 text-xs text-text-secondary">
                    {gaps.map((gap, i) => (
                      <li key={i} className="flex justify-between">
                        <span>
                          {formatDateTime(gap.start)} → {formatDateTime(gap.end)}
                        </span>
                        <span className="font-medium text-semantic-danger">
                          {interpolate(uiStrings.auditoria.continuityGapDurationMin, {
                            minutes: Math.round(gap.duration_minutes),
                          })}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
