import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTailRisk } from "@/hooks/queries/useRisk";
import { formatPercent } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.7 "Tail Risk (VaR/CVaR, 60d)". `verdict` de la API YA es el
// texto de aviso completo (services/risk.py::RiskServiceConfig.verdict_ok/
// verdict_breach) -- se muestra tal cual, sin reconstruirlo. La etiqueta
// corta del badge (GREEN/RED) se deriva de `breached`, no viene de la API.
export function TailRiskCard() {
  const { data } = useTailRisk();

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>{interpolate(uiStrings.riesgo.tailRiskTitle, { window: 60 })}</CardTitle>
        {data && (
          <Badge variant={data.breached ? "danger" : "success"}>
            {data.breached ? uiStrings.riesgo.tailVerdictBreach : uiStrings.riesgo.tailVerdictOk}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {!data && <p className="text-sm text-text-secondary">{uiStrings.riesgo.emptyTailRisk}</p>}
        {data && (
          <>
            <dl className="grid grid-cols-3 gap-x-3 gap-y-2 text-xs">
              <div>
                <dt className="text-text-secondary">{uiStrings.riesgo.colVar95}</dt>
                <dd className="text-text-primary">{formatPercent(data.var95_daily)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.riesgo.colVar99}</dt>
                <dd className="text-text-primary">{formatPercent(data.var99_daily)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.riesgo.colCvar99}</dt>
                <dd className="text-text-primary">{formatPercent(data.cvar99_daily)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.riesgo.colCvar95}</dt>
                <dd className="text-text-primary">{formatPercent(data.cvar95_daily)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.riesgo.colCvar99Monthly}</dt>
                <dd className="text-text-primary">{formatPercent(data.cvar99_monthly)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.riesgo.colCvar99Annual}</dt>
                <dd className="text-text-primary">{formatPercent(data.cvar99_annual)}</dd>
              </div>
            </dl>
            <p className="text-xs text-text-secondary">{data.verdict}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
