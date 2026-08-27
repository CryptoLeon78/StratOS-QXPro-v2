import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WatchdogStateBadge } from "@/components/domain/WatchdogStateBadge";
import { useBots } from "@/hooks/queries/useBots";
import { useWatchdog } from "@/hooks/queries/useExecution";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.10 "Watchdog de bots": GET /execution/watchdog, cruzado con
// GET /bots para el nombre (WatchdogRow solo trae bot_id/magic_number).
export function WatchdogTable() {
  const { data: rows } = useWatchdog();
  const { data: bots } = useBots();
  const botNameById = new Map((bots ?? []).map((bot) => [bot.id, bot.name]));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.ejecucion.watchdogTitle}</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-secondary">
              <th className="pb-1 font-normal">{uiStrings.ejecucion.colBot}</th>
              <th className="pb-1 font-normal">{uiStrings.ejecucion.colExpectedMonth}</th>
              <th className="pb-1 font-normal">{uiStrings.ejecucion.colObserved30d}</th>
              <th className="pb-1 font-normal">{uiStrings.ejecucion.colLastTrade}</th>
              <th className="pb-1 font-normal">{uiStrings.ejecucion.colState}</th>
            </tr>
          </thead>
          <tbody>
            {(rows ?? []).map((row) => (
              <tr key={row.bot_id} className="border-t border-border-subtle">
                <td className="py-1.5 text-text-primary">
                  {botNameById.get(row.bot_id) ?? `#${row.bot_id}`}{" "}
                  <span className="text-xs text-text-secondary">#{row.magic_number}</span>
                </td>
                <td className="py-1.5">{row.expected_month ?? "—"}</td>
                <td className="py-1.5">{row.observed_30d}</td>
                <td className="py-1.5 text-text-secondary">
                  {row.last_trade_at ? new Date(row.last_trade_at).toLocaleDateString("es-ES") : "—"}
                </td>
                <td className="py-1.5">
                  <WatchdogStateBadge state={row.state} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
