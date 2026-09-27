import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { CauseBadge } from "@/components/domain/CauseBadge";
import { useAttemptReactivation } from "@/hooks/queries/useCemetery";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { CemeteryEntry } from "@/api/endpoints/cemetery";
import type { BotRow } from "@/api/endpoints/bots";

// PARTE 7.8: tarjeta de Graveyard. Fecha de INICIO del rango de la captura
// (docs/adr/0006) sale de `entered_pipeline_at` cuando el rastro append-only
// PipelinePhaseTransition la conserva (candidatos admitidos desde G11); para
// un bot sin ese rastro se cae a mostrar solo `retired_at` -- ausencia
// declarada, nunca una fecha inventada. Reactivacion: boton informativo,
// SIEMPRE 409 (P6.3 "sin retorno"), nunca un flujo de exito real.
export function CemeteryCard({ entry, bot }: { entry: CemeteryEntry; bot: BotRow | undefined }) {
  const reactivate = useAttemptReactivation();
  const [reason, setReason] = useState<string | null>(null);
  const retiredAt = new Date(entry.retired_at).toLocaleDateString("es-ES");
  const dateLabel = entry.entered_pipeline_at
    ? interpolate(uiStrings.graveyard.dateRange, {
        from: new Date(entry.entered_pipeline_at).toLocaleDateString("es-ES"),
        to: retiredAt,
      })
    : retiredAt;

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0 p-3">
        <div>
          <p className="text-sm font-semibold text-text-primary">
            {bot?.name ?? `Bot #${entry.bot_id}`} <span className="text-xs text-text-secondary">#{bot?.magic_number}</span>
          </p>
          <p className="text-xs text-text-secondary">
            {bot ? `${bot.profile?.toLowerCase() ?? "—"} · ${bot.market}` : ""} · {dateLabel}
          </p>
        </div>
        <CauseBadge cause={entry.cause} />
      </CardHeader>
      <CardContent className="space-y-2 p-3 pt-0">
        <p className="text-xs text-text-secondary">"{entry.autopsy_text}"</p>
        <Button
          size="sm"
          variant="outline"
          disabled={reactivate.isPending}
          onClick={() =>
            reactivate.mutate(entry.bot_id, { onSuccess: (msg) => setReason(msg) })
          }
        >
          {uiStrings.graveyard.reactivate}
        </Button>
        {reason && (
          <p className="text-xs text-semantic-danger">
            {interpolate(uiStrings.graveyard.reactivateBlocked, { reason })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
