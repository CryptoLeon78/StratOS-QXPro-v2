import { Badge } from "@/components/ui/badge";
import { useDataProvenance } from "@/hooks/queries/useDataProvenance";
import type { DataOrigin, TradeAttributionCoverage } from "@/api/endpoints/provenance";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// Procedencia del dato en las vistas AGREGADAS (Portfolio, Salud, Riesgo, Auditoria,
// Dominical). En Bots, Pipeline y Cuentas/EA cada fila declara la suya y no hace falta esto.
//
// El recorrido G12 encontro que estas superficies sumaban fixture y telemetria real en la
// misma cifra sin que nada lo dijera, y por eso el operador no podia fiarse de los numeros.
// El caso que importa es `is_mixed`: con un solo origen las cifras significan una cosa, con
// varios cualquier total agrega universos distintos.
const VARIANT: Record<DataOrigin, "success" | "warning" | "default"> = {
  BROKER_REAL: "success",
  BROKER_DEMO: "warning",
  FIXTURE: "default",
};

function originLabel(origin: DataOrigin): string {
  return uiStrings.provenance[origin] ?? origin;
}

export function ProvenanceBadge() {
  const { data } = useDataProvenance();

  // Mientras carga no se afirma nada: una procedencia equivocada es peor que ninguna.
  if (!data) return null;

  if (data.accounts.length === 0) {
    return (
      <p className="text-xs text-text-muted" data-testid="provenance">
        {uiStrings.provenance.absent}
      </p>
    );
  }

  const origins = data.accounts.map((row) => originLabel(row.data_origin));

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="provenance">
      <span className="text-xs text-text-muted">{uiStrings.provenance.label}:</span>
      {data.accounts.map((row) => (
        <Badge key={row.data_origin} variant={VARIANT[row.data_origin] ?? "default"}>
          {originLabel(row.data_origin)} ·{" "}
          {interpolate(uiStrings.provenance.counts, {
            accounts: row.accounts,
            bots: row.bots,
          })}
        </Badge>
      ))}
      <span className="text-xs text-text-secondary">
        {data.is_mixed
          ? interpolate(uiStrings.provenance.mixedDetail, { origins: origins.join(" + ") })
          : interpolate(uiStrings.provenance.single, { origin: origins[0] })}
      </span>
      <span className="text-xs text-text-muted" data-testid="attribution">
        {attributionText(data.trade_attribution)}
      </span>
    </div>
  );
}

// Cuanta de la cifra agregada pertenece a un bot vivo. Las metricas POR BOT ya cubren solo
// EAs vivos --un EA retirado no tiene fila en `bot`--, pero un total de Portfolio o Riesgo
// suma tambien los trades de EAs retirados y los del historico sin magic. Decision del
// operador: los retirados no se inventarian ni se presentan, pero el total dice cuanto de el
// no es de ningun bot vivo, en vez de pasar por ser todo del portfolio actual.
function attributionText(a: TradeAttributionCoverage): string {
  if (a.total === 0 || a.coverage_pct === null) return uiStrings.provenance.attributionAbsent;
  if (a.attributed_to_live_bot === a.total) {
    return interpolate(uiStrings.provenance.attributionFull, { total: a.total });
  }
  return interpolate(uiStrings.provenance.attribution, {
    coverage: a.coverage_pct,
    total: a.total,
    retired: a.retired_ea,
    without: a.without_ea,
  });
}
