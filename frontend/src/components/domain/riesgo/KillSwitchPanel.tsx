import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useKillSwitchLadder } from "@/hooks/queries/useConfig";
import { useConfirmDeescalation, useKillSwitchStatus } from "@/hooks/queries/useKillSwitch";
import { formatPercent } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.7 "Drawdown y kill-switch": DD actual (GET /killswitch/status) +
// escalera L1-L4 estatica (GET /config/killswitch-ladder, nuevo en G7).
// MAX DD/DURACION DD (G10, grupo g): episode_max_dd_pct/episode_duration_seconds
// -- null mientras el episodio de DD>0 no exista (portfolio en DD 0%, nunca
// se inventan).
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
        <div className="grid grid-cols-3 gap-x-3 text-xs">
          <div>
            <p className="text-text-secondary">{uiStrings.riesgo.ddActual}</p>
            <p className="text-lg font-semibold text-text-primary">
              {status ? formatPercent(status.portfolio_dd_pct ?? 0) : "—"}
            </p>
          </div>
          <div>
            <p className="text-text-secondary">{uiStrings.riesgo.maxDdEpisode}</p>
            <p className="text-lg font-semibold text-text-primary">
              {status?.episode_max_dd_pct === null || status?.episode_max_dd_pct === undefined
                ? "—"
                : formatPercent(status.episode_max_dd_pct)}
            </p>
          </div>
          <div>
            <p className="text-text-secondary">{uiStrings.riesgo.durationDdEpisode}</p>
            <p className="text-lg font-semibold text-text-primary">
              {status?.episode_duration_seconds === null ||
              status?.episode_duration_seconds === undefined
                ? "—"
                : interpolate(uiStrings.riesgo.durationDdDays, {
                    days: Math.round(status.episode_duration_seconds / 86400),
                  })}
            </p>
          </div>
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
