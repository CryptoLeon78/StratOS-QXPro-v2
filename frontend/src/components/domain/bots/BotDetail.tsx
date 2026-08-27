import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ImpulseFormDialog } from "@/components/domain/bots/ImpulseFormDialog";
import { SemaphoreBadge } from "@/components/domain/SemaphoreBadge";
import { useBotSemaphoreHistory } from "@/hooks/queries/useBots";
import { useHealthBots } from "@/hooks/queries/useHealth";
import { useSemaphoreInstructions } from "@/hooks/queries/useConfig";
import { formatPercent } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { BotRow } from "@/api/endpoints/bots";

function instructionFor(
  state: string,
  magicNumber: number,
  instructions: { verde: string; amarillo: string; naranja_template: string } | undefined
): string | null {
  if (!instructions) return null;
  if (state === "VERDE") return instructions.verde;
  if (state === "AMARILLO") return instructions.amarillo;
  if (state === "NARANJA") return interpolate(instructions.naranja_template, { magic: magicNumber });
  return null;
}

// PARTE 7.4, panel de detalle. P&L acumulado/Metricas completas/
// Posiciones abiertas/Histograma de retornos/Historial del pipeline de la
// captura se OMITEN aqui (sin endpoint que los sirva, docs/backlog.md) --
// "Historial del pipeline" se sustituye por "Historial de semaforo" (ADR:
// bots-historial-semaforo-no-pipeline), dato real disponible en el mismo
// lugar del layout.
export function BotDetail({ bot }: { bot: BotRow }) {
  const [impulseOpen, setImpulseOpen] = useState(false);
  const { data: instructions } = useSemaphoreInstructions();
  const { data: healthRows } = useHealthBots();
  const { data: semaphoreHistory } = useBotSemaphoreHistory(bot.id);
  const health = (healthRows ?? []).find((row) => row.bot_id === bot.id);
  const instructionText = instructionFor(bot.semaphore_state, bot.magic_number, instructions);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div>
            <CardTitle>{bot.name}</CardTitle>
            <p className="text-xs text-text-secondary">
              magic {bot.magic_number} · {bot.market} {bot.timeframe} · {bot.profile.toLowerCase()}{" "}
              · {bot.pipeline_phase} · {bot.role.toLowerCase()}
            </p>
          </div>
          <SemaphoreBadge state={bot.semaphore_state} />
        </CardHeader>
        <CardContent className="space-y-3">
          {instructionText && <p className="text-sm text-text-secondary">{instructionText}</p>}
          <Button variant="outline" size="sm" onClick={() => setImpulseOpen(true)}>
            {uiStrings.bots.impulseButton}
          </Button>
        </CardContent>
      </Card>

      {health && (
        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.rollingVsBaselineTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-secondary">
                  <th className="pb-1 font-normal" />
                  <th className="pb-1 font-normal">{uiStrings.bots.colRolling}</th>
                  <th className="pb-1 font-normal">{uiStrings.bots.colBaseline}</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-border-subtle">
                  <td className="py-1.5">{uiStrings.bots.rowProfitFactor}</td>
                  <td className="py-1.5">{health.pf_rolling.toFixed(2)}</td>
                  <td className="py-1.5 text-text-secondary">{health.pf_baseline.toFixed(2)}</td>
                </tr>
                <tr className="border-t border-border-subtle">
                  <td className="py-1.5">{uiStrings.bots.rowExpectancy}</td>
                  <td className="py-1.5">{health.exp_rolling.toFixed(2)}</td>
                  <td className="py-1.5 text-text-secondary">{health.exp_baseline.toFixed(2)}</td>
                </tr>
                <tr className="border-t border-border-subtle">
                  <td className="py-1.5">{uiStrings.bots.rowLossStreak}</td>
                  <td className="py-1.5" colSpan={2}>
                    {health.loss_streak}
                  </td>
                </tr>
                <tr className="border-t border-border-subtle">
                  <td className="py-1.5">{uiStrings.bots.rowDdRolling}</td>
                  <td className="py-1.5">{formatPercent(health.dd_bot_pct)}</td>
                  <td className="py-1.5 text-text-secondary">
                    {formatPercent(health.dd_contract_pct)}
                  </td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.semaphoreHistoryTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            {(semaphoreHistory ?? []).length === 0 && (
              <p className="text-sm text-text-secondary">
                {uiStrings.bots.emptySemaphoreHistory}
              </p>
            )}
            <ul className="space-y-2">
              {(semaphoreHistory ?? []).map((entry) => (
                <li key={entry.id} className="text-xs">
                  <span className="text-text-secondary">
                    {new Date(entry.ts).toLocaleDateString("es-ES")}
                  </span>{" "}
                  <Badge variant="outline">{entry.from_state}</Badge> →{" "}
                  <Badge variant="outline">{entry.to_state}</Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.bots.contributionTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-text-secondary">{uiStrings.bots.sizingObjetivo}</p>
            <p className="text-lg font-semibold text-text-primary">
              {bot.capital_allocated_pct}%
            </p>
          </CardContent>
        </Card>
      </div>

      <ImpulseFormDialog
        botId={bot.id}
        botName={bot.name}
        open={impulseOpen}
        onOpenChange={setImpulseOpen}
      />
    </div>
  );
}
