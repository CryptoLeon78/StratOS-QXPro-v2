import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useNewsShield, useNewsShieldTrades } from "@/hooks/queries/useNews";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { TradeInNewsWindow } from "@/api/endpoints/news";

const DEFAULT_NEWS_SHIELD_HOURS = 48;

function formatHhmm(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Madrid",
  });
}

interface BotNewsTradeSummary {
  botName: string;
  count: number;
  lastNewsTitle: string;
}

// Agrupa por bot y toma la noticia mas reciente (news_ts) por bot -- "N
// trade(s) ejecutado(s) en ventana (ultimo: <titulo>)" de la captura.
function summarizeByBot(trades: TradeInNewsWindow[]): BotNewsTradeSummary[] {
  const byBot = new Map<string, TradeInNewsWindow[]>();
  for (const t of trades) {
    const key = t.bot_name ?? "—";
    byBot.set(key, [...(byBot.get(key) ?? []), t]);
  }
  return [...byBot.entries()].map(([botName, botTrades]) => {
    const latest = botTrades.reduce((a, b) => (a.news_ts > b.news_ts ? a : b));
    return { botName, count: botTrades.length, lastNewsTitle: latest.news_title };
  });
}

// PARTE 7.7 "News Shield": GET /news/shield?hours=48 + "Trades en ventana de
// noticias (30 dias)" (G10, GET /news/shield/trades) agrupado por bot.
// `hours` es prop (default 48, comportamiento sin cambios en Riesgo) para
// que la vista dominical (grupo n) pueda reusar el mismo componente con
// una ventana de 7 dias ("semana entrante") sin duplicar la logica.
export function NewsShieldPanel({ hours = DEFAULT_NEWS_SHIELD_HOURS }: { hours?: number } = {}) {
  const { data } = useNewsShield(hours);
  const { data: tradesInWindow } = useNewsShieldTrades();
  const botSummaries = useMemo(() => summarizeByBot(tradesInWindow ?? []), [tradesInWindow]);
  const [copied, setCopied] = useState(false);

  const windowsText = (data ?? [])
    .map((row) => `${formatHhmm(row.window_start)}-${formatHhmm(row.window_end)}`)
    .join(";");

  async function copyWindows() {
    await navigator.clipboard.writeText(windowsText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{interpolate(uiStrings.riesgo.newsShieldTitle, { hours })}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <table className="w-full text-sm">
          <tbody>
            {(data ?? []).map((row) => (
              <tr key={row.id} className="border-t border-border-subtle first:border-t-0">
                <td className="py-1.5 font-medium text-text-primary">{row.title}</td>
                <td className="py-1.5 text-text-secondary">{row.currency}</td>
                <td className="py-1.5 text-text-secondary">
                  {formatHhmm(row.window_start)}–{formatHhmm(row.window_end)}
                </td>
                <td className="py-1.5 text-xs text-text-muted">
                  {row.affected_bots.join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(data ?? []).length > 0 && (
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate text-xs text-text-secondary">{windowsText}</code>
            <Button variant="outline" size="sm" onClick={copyWindows}>
              {copied ? "✓" : uiStrings.riesgo.copyWindows}
            </Button>
          </div>
        )}
        <div>
          <p className="text-xs font-medium text-text-secondary">
            {uiStrings.riesgo.tradesInWindowTitle}
          </p>
          {botSummaries.length === 0 ? (
            <p className="text-xs text-text-muted">{uiStrings.riesgo.emptyTradesInWindow}</p>
          ) : (
            <ul className="space-y-0.5 text-xs text-text-secondary">
              {botSummaries.map((s) => (
                <li key={s.botName}>
                  {interpolate(uiStrings.riesgo.tradesInWindowRow, {
                    bot: s.botName,
                    count: s.count,
                    news: s.lastNewsTitle,
                  })}
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
