import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuditStatus, useRunAudit } from "@/hooks/queries/useAudit";
import { formatAmount, formatPercent } from "@/lib/formatters";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.9 "Reconciliacion contable": GET /audit/status (por cuenta) +
// boton "Ejecutar auditoria ahora" -> POST /audit/run.
export function ReconciliationCard() {
  const { data } = useAuditStatus();
  const runAudit = useRunAudit();

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>{uiStrings.auditoria.reconciliationTitle}</CardTitle>
        <Button size="sm" variant="outline" disabled={runAudit.isPending} onClick={() => runAudit.mutate()}>
          {uiStrings.auditoria.runNow}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {(data ?? []).map((row) => (
          <div key={row.account_id} className="space-y-1 border-t border-border-subtle pt-2 first:border-t-0 first:pt-0">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">Cuenta #{row.account_id}</span>
              <Badge variant={row.breached ? "danger" : "success"}>
                {row.breached ? uiStrings.auditoria.statusBreach : uiStrings.auditoria.statusOk}
              </Badge>
            </div>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              <div>
                <dt className="text-text-secondary">{uiStrings.auditoria.colInitialBalance}</dt>
                <dd className="text-text-primary">{formatAmount(row.initial_balance)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.auditoria.colFlows}</dt>
                <dd className="text-text-primary">{formatAmount(row.flows)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.auditoria.colExpected}</dt>
                <dd className="text-text-primary">{formatAmount(row.expected)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.auditoria.colReported}</dt>
                <dd className="text-text-primary">{formatAmount(row.final_balance)}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-text-secondary">{uiStrings.auditoria.colDiscrepancy}</dt>
                <dd className={row.breached ? "text-semantic-danger" : "text-semantic-success"}>
                  {row.discrepancy_pct !== null ? formatPercent(row.discrepancy_pct) : "—"}
                </dd>
              </div>
            </dl>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
