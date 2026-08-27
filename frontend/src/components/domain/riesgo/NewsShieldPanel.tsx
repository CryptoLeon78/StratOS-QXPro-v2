import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useNewsShield } from "@/hooks/queries/useNews";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

const NEWS_SHIELD_HOURS = 48;

function formatHhmm(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Madrid",
  });
}

// PARTE 7.7 "News Shield": GET /news/shield?hours=48. "Trades en ventana de
// noticias (30 dias)" de la captura no esta en NewsShieldRow (ningun
// endpoint cruza trades x ventanas) -- omitido, docs/backlog.md.
export function NewsShieldPanel() {
  const { data } = useNewsShield(NEWS_SHIELD_HOURS);
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
        <CardTitle>
          {interpolate(uiStrings.riesgo.newsShieldTitle, { hours: NEWS_SHIELD_HOURS })}
        </CardTitle>
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
      </CardContent>
    </Card>
  );
}
