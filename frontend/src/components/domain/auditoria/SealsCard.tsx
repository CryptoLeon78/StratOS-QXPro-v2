import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSealsSummary } from "@/hooks/queries/useAudit";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.9 "Sellos de integridad": GET /audit/seals, mapeo directo --
// disclaimer literal de P6/7.9.
export function SealsCard() {
  const { data } = useSealsSummary();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.auditoria.sealsTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {data && (
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-text-secondary">{uiStrings.auditoria.sealedBatches}</p>
              <p className="text-lg font-semibold text-text-primary">{data.total_batches}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{uiStrings.auditoria.archivedTrades}</p>
              <p className="text-lg font-semibold text-text-primary">{data.total_trades}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{uiStrings.auditoria.tickets}</p>
              <p className="text-sm text-text-primary">
                {data.ticket_min ?? "—"} → {data.ticket_max ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">{uiStrings.auditoria.history}</p>
              <p className="text-sm text-text-primary">
                {data.history_start ? new Date(data.history_start).toLocaleDateString("es-ES") : "—"} →{" "}
                {data.history_end ? new Date(data.history_end).toLocaleDateString("es-ES") : "—"}
              </p>
            </div>
          </div>
        )}
        <p className="text-xs text-text-muted">{uiStrings.auditoria.disclaimer}</p>
      </CardContent>
    </Card>
  );
}
