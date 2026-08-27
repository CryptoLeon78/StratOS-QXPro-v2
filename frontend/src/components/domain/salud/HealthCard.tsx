import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SemaphoreBadge } from "@/components/domain/SemaphoreBadge";
import { useSemaphoreInstructions } from "@/hooks/queries/useConfig";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { HealthRow } from "@/api/endpoints/health";

// PARTE 7.6: tarjeta de Salud por bot. Solo 3 de los "chips" de la captura
// tienen dato real (PF/Expectancy rolling, DD rolling, Racha de perdidas)
// -- Sharpe rolling/Win Rate drift/Payoff/Duracion media NO tienen formula
// (docs/backlog.md, gap ya documentado en G5), se omiten en vez de
// mostrarse vacios. PH: solo existe `page_hinkley_triggered` (bool), no un
// valor numerico como el "PH 1.3" de la captura -- se muestra Si/No (ADR).
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

export function HealthCard({ bot }: { bot: HealthRow }) {
  const { data: instructions } = useSemaphoreInstructions();
  const instructionText = instructionFor(bot.semaphore_state, bot.magic_number, instructions);

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <p className="font-semibold text-text-primary">{bot.name}</p>
          <p className="text-xs text-text-secondary">
            {bot.profile.toLowerCase()} · {bot.pipeline_phase} ·{" "}
            {interpolate(uiStrings.salud.daysInState, { days: bot.days_in_state })}
          </p>
        </div>
        <SemaphoreBadge state={bot.semaphore_state} />
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="outline">{uiStrings.salud.chipPfExpectancy}</Badge>
          <Badge variant="outline">{uiStrings.salud.chipDdRolling}</Badge>
          <Badge variant="outline">{uiStrings.salud.chipLossStreak}</Badge>
          <Badge variant={bot.page_hinkley_triggered ? "danger" : "outline"}>
            {interpolate(uiStrings.salud.chipPageHinkley, {
              value: bot.page_hinkley_triggered ? "Sí" : "No",
            })}
          </Badge>
        </div>
        {instructionText && (
          <p className="rounded-md bg-bg-surfaceHover px-2 py-1.5 text-xs text-text-secondary">
            {instructionText}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
