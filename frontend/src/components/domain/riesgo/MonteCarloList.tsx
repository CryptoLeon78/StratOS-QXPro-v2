import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBots } from "@/hooks/queries/useBots";
import { useMonteCarloHistory } from "@/hooks/queries/useRisk";
import { formatPercent } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { BotRow } from "@/api/endpoints/bots";

const ACTIVE_PHASES = new Set(["F7", "PRODUCCION"]);

// PARTE 7.7 "Drawdown esperado (Monte Carlo) y contrato de drawdown": una
// tarjeta por bot activo. GET /risk/montecarlo/history (G10, todas las
// runs, mas recientes primero) en vez de /montecarlo (solo la ultima) --
// "Historico" de la captura son las runs anteriores; la fecha de firma del
// contrato es `ts` de la run vigente (ya estaba en el schema desde G5).
function MonteCarloRow({ bot }: { bot: BotRow }) {
  const { data: history } = useMonteCarloHistory(bot.id);
  const [latest, ...previous] = history ?? [];

  if (!latest) {
    return (
      <div className="border-t border-border-subtle py-2 first:border-t-0">
        <p className="font-medium text-text-primary">{bot.name}</p>
        <p className="text-xs text-text-secondary">{uiStrings.riesgo.emptyMonteCarlo}</p>
      </div>
    );
  }

  const breach = Number(latest.dd_p95) > Number(latest.dd_contract_pct);

  return (
    <div className="border-t border-border-subtle py-2 first:border-t-0">
      <div className="flex items-center justify-between">
        <p className="font-medium text-text-primary">
          {bot.name} <span className="text-xs text-text-secondary">magic {bot.magic_number}</span>
        </p>
        <Badge variant={breach ? "warning" : "success"}>
          {breach ? uiStrings.riesgo.monteCarloBreach : uiStrings.riesgo.monteCarloWithinProfile}
        </Badge>
      </div>
      <p className="text-xs text-text-secondary">
        P50: {formatPercent(latest.dd_p50)} · P75: {formatPercent(latest.dd_p75)} · P95:{" "}
        {formatPercent(latest.dd_p95)} ·{" "}
        {interpolate(uiStrings.riesgo.contractSigned, {
          pct: formatPercent(latest.dd_contract_pct),
          date: new Date(latest.ts).toLocaleDateString("es-ES"),
        })}
      </p>
      {previous.length > 0 && (
        <p className="text-xs text-text-muted">
          {uiStrings.riesgo.historicoLabel}{" "}
          {previous
            .map((run) => `${formatPercent(run.dd_p95)} (${new Date(run.ts).toLocaleDateString("es-ES")})`)
            .join(" · ")}
        </p>
      )}
    </div>
  );
}

export function MonteCarloList() {
  const { data: bots } = useBots();
  const active = (bots ?? []).filter((bot) => ACTIVE_PHASES.has(bot.pipeline_phase));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.riesgo.monteCarloTitle}</CardTitle>
      </CardHeader>
      <CardContent>
        {active.map((bot) => (
          <MonteCarloRow key={bot.id} bot={bot} />
        ))}
      </CardContent>
    </Card>
  );
}
