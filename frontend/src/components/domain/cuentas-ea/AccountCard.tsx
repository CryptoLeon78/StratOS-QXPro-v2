import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAccountEas } from "@/hooks/queries/useAccounts";
import { useHeartbeat } from "@/hooks/queries/useExecution";
import { formatPercent } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { AccountRow } from "@/api/endpoints/accounts";
import type { BotRow } from "@/api/endpoints/bots";

// PARTE 7.2 (diseño derivado, sin captura de referencia). Equity/balance/
// margen libre/margin level de la spec NO estan en AccountResponse --
// omitidos (docs/backlog.md); conexion/heartbeat/latencia/uptime
// reutilizan GET /execution/heartbeat por account_id. `ea_required_version`
// no existe -- solo se muestra la version reportada, sin badge de
// desactualizada.
export function AccountCard({ account, bots }: { account: AccountRow; bots: BotRow[] }) {
  const { data: eas } = useAccountEas(account.id);
  const { data: heartbeats } = useHeartbeat();
  const heartbeat = (heartbeats ?? []).find((h) => h.account_id === account.id);
  const accountBots = bots.filter((bot) => bot.account_id === account.id);
  const botByMagic = new Map(accountBots.map((bot) => [bot.magic_number, bot]));

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle>{account.name}</CardTitle>
          <p className="text-xs text-text-secondary">
            {account.broker} · {account.server} · {account.login} · {account.currency}
          </p>
        </div>
        <Badge variant={account.is_demo ? "outline" : "default"}>
          {account.is_demo ? uiStrings.cuentasEa.demo : uiStrings.cuentasEa.real}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* G9: los 3 spans de detalle SIEMPRE ocupan su sitio (invisible en
        vez de ausentes cuando no aplican) -- montarlos/desmontarlos segun
        heartbeat?.connected desplazaba verticalmente todo el contenido de
        abajo (deriva de configuracion, TCA...) cada vez que una cuenta
        cruzaba de "conectada" a "desconectada" entre la captura del
        baseline de Playwright y la corrida del test -- carrera de tiempo
        real que rompio cuentas_ea.spec.ts en CI (ver ASSUMPTIONS
        G9-06/G9-07); ninguna mascara compensa un cambio de altura de
        pagina, solo una altura estable lo resuelve de raiz. */}
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`inline-block size-2 rounded-full ${
              heartbeat?.connected ? "bg-semantic-success" : "bg-text-muted"
            }`}
          />
          <span className={heartbeat?.connected ? "text-semantic-success" : "text-text-secondary"}>
            {heartbeat?.connected ? uiStrings.cuentasEa.connected : uiStrings.cuentasEa.disconnected}
          </span>
          <span className={`text-text-secondary ${heartbeat?.last_ts ? "" : "invisible"}`}>
            {interpolate(uiStrings.cuentasEa.lastHeartbeat, {
              date: heartbeat?.last_ts
                ? new Date(heartbeat.last_ts).toLocaleString("es-ES", { timeZone: "Europe/Madrid" })
                : " ",
            })}
          </span>
          <span
            className={`text-text-secondary ${
              heartbeat?.latency_ms !== null && heartbeat?.latency_ms !== undefined ? "" : "invisible"
            }`}
          >
            {interpolate(uiStrings.cuentasEa.latency, { ms: heartbeat?.latency_ms ?? 0 })}
          </span>
          <span className={`text-text-secondary ${heartbeat ? "" : "invisible"}`}>
            {interpolate(uiStrings.cuentasEa.uptime7d, {
              pct: formatPercent(heartbeat?.uptime_pct_7d ?? 0),
            })}
          </span>
        </div>

        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-text-secondary">
              <th className="pb-1 font-normal">{uiStrings.cuentasEa.colMagic}</th>
              <th className="pb-1 font-normal">{uiStrings.cuentasEa.colBot}</th>
              <th className="pb-1 font-normal">{uiStrings.cuentasEa.colPhaseRole}</th>
              <th className="pb-1 font-normal">{uiStrings.cuentasEa.colEaVersion}</th>
              <th className="pb-1 font-normal">{uiStrings.cuentasEa.colAutotrading}</th>
            </tr>
          </thead>
          <tbody>
            {(eas ?? []).map((ea) => {
              const bot = botByMagic.get(ea.magic_number);
              return (
                <tr key={ea.magic_number} className="border-t border-border-subtle">
                  <td className="py-1.5">{ea.magic_number}</td>
                  <td className="py-1.5 text-text-primary">{bot?.name ?? "—"}</td>
                  <td className="py-1.5 text-text-secondary">
                    {bot ? `${bot.pipeline_phase} · ${bot.role.toLowerCase()}` : "—"}
                  </td>
                  <td className="py-1.5 text-text-secondary">{ea.ea_version}</td>
                  <td className="py-1.5">
                    <Badge variant={ea.autotrading ? "success" : "outline"}>
                      {ea.autotrading ? "ON" : "OFF"}
                    </Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
