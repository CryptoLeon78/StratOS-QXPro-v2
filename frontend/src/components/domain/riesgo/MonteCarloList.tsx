import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBots } from "@/hooks/queries/useBots";
import { useMonteCarlo } from "@/hooks/queries/useRisk";
import { formatPercent } from "@/lib/formatters";
import uiStrings from "@/styles/ui_strings.es.json";
import type { BotRow } from "@/api/endpoints/bots";

const ACTIVE_PHASES = new Set(["F7", "PRODUCCION"]);

// PARTE 7.7 "Drawdown esperado (Monte Carlo) y contrato de drawdown": una
// tarjeta por bot activo, GET /risk/montecarlo?bot_id=. "Historico" DD% y
// fecha de firma del contrato de la captura no estan en MonteCarloResponse
// -- se omiten (docs/backlog.md), solo P50/P75/P95/contrato.
function MonteCarloRow({ bot }: { bot: BotRow }) {
  const { data } = useMonteCarlo(bot.id);

  if (!data) {
    return (
      <div className="border-t border-border-subtle py-2 first:border-t-0">
        <p className="font-medium text-text-primary">{bot.name}</p>
        <p className="text-xs text-text-secondary">{uiStrings.riesgo.emptyMonteCarlo}</p>
      </div>
    );
  }

  const breach = Number(data.dd_p95) > Number(data.dd_contract_pct);

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
        P50: {formatPercent(data.dd_p50)} · P75: {formatPercent(data.dd_p75)} · P95:{" "}
        {formatPercent(data.dd_p95)} · Contrato: {formatPercent(data.dd_contract_pct)}
      </p>
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
