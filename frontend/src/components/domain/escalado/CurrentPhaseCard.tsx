import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useUmsPhasesConfig } from "@/hooks/queries/useConfig";
import { useCurrentUmsPhase } from "@/hooks/queries/useScaling";
import { formatAmount } from "@/lib/formatters";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.9 "Fase UMS actual": GET /scaling/ums (fase/equity_at/
// ready_to_advance reales) + descripcion estatica de la fase desde el
// nuevo GET /config/ums-phases (riesgo/op, Kelly -- no vienen en
// UmsPhaseResponse).
export function CurrentPhaseCard() {
  const { data: current } = useCurrentUmsPhase();
  const { data: phases } = useUmsPhasesConfig();
  const phaseDef = phases?.find((p) => p.phase === current?.phase);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.escalado.currentPhaseTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!current && <p className="text-sm text-text-secondary">{uiStrings.escalado.emptyCurrentPhase}</p>}
        {current && phaseDef && (
          <>
            <div>
              <p className="text-lg font-semibold text-text-primary">
                {phaseDef.phase} · {phaseDef.name}
              </p>
              <p className="text-xs text-text-secondary">
                Equity: {formatAmount(current.equity_at)} · Riesgo/op:{" "}
                {phaseDef.risk_per_trade_pct_min && phaseDef.risk_per_trade_pct_max
                  ? `${phaseDef.risk_per_trade_pct_min}-${phaseDef.risk_per_trade_pct_max}%`
                  : (phaseDef.risk_note ?? "—")}{" "}
                · Kelly {phaseDef.kelly_fraction}
              </p>
            </div>
            <Badge variant={current.ready_to_advance ? "success" : "outline"}>
              {current.ready_to_advance ? uiStrings.escalado.readyToAdvance : uiStrings.escalado.notReady}
            </Badge>
          </>
        )}
      </CardContent>
    </Card>
  );
}
