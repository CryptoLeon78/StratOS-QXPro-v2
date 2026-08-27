import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useKillSwitchLadder } from "@/hooks/queries/useConfig";
import { useConfirmDeescalation, useKillSwitchStatus } from "@/hooks/queries/useKillSwitch";
import { formatPercent } from "@/lib/formatters";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.7 "Drawdown y kill-switch": DD actual (GET /killswitch/status) +
// escalera L1-L4 estatica (GET /config/killswitch-ladder, nuevo en G7).
// MAX DD/DURACION DD de la captura no estan en KillSwitchStatusResponse --
// se omiten (docs/backlog.md), solo se muestra DD actual.
export function KillSwitchPanel() {
  const { data: status } = useKillSwitchStatus();
  const { data: ladder } = useKillSwitchLadder();
  const deescalate = useConfirmDeescalation();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.riesgo.killswitchTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-xs text-text-secondary">{uiStrings.riesgo.ddActual}</p>
          <p className="text-lg font-semibold text-text-primary">
            {status ? formatPercent(status.portfolio_dd_pct ?? 0) : "—"}
          </p>
        </div>
        <ul className="space-y-1.5 text-xs">
          {(ladder ?? []).map((level) => (
            <li
              key={level.level}
              className={`flex gap-2 rounded-md px-2 py-1 ${
                status?.level === level.level ? "bg-bg-surfaceHover" : ""
              }`}
            >
              <span className="font-semibold text-text-primary">
                L{level.level} · &gt;{level.threshold_pct}%
              </span>
              <span className="text-text-secondary">{level.instruction_text}</span>
            </li>
          ))}
        </ul>
        {status && status.level > 0 && (
          <Button
            variant="outline"
            size="sm"
            disabled={deescalate.isPending}
            onClick={() => deescalate.mutate()}
          >
            {uiStrings.riesgo.confirmDeescalation}
          </Button>
        )}
        <p className="text-xs text-text-muted">{uiStrings.riesgo.killswitchNote}</p>
        {status && status.level > 0 && <Badge variant="warning">KS L{status.level}</Badge>}
      </CardContent>
    </Card>
  );
}
