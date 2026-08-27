import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAccountsDrift } from "@/hooks/queries/useAccounts";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.2 "Panel Deriva de configuracion": GET /accounts/drift, mapeo
// directo. La spec pide tambien sizing aplicado vs sizing_current_pct y
// magics huerfanos/ausentes -- DriftRowResponse solo trae deriva de modo
// (expected_mode vs reported_mode), asi que el panel se limita a eso
// (coincide con el caso de uso literal de CLAUDE.md: "EA en modo
// incorrecto").
export function DriftPanel() {
  const { data } = useAccountsDrift();
  const drifted = (data ?? []).filter((row) => row.drift);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.cuentasEa.driftTitle}</CardTitle>
      </CardHeader>
      <CardContent>
        {drifted.length === 0 && (
          <p className="text-sm text-semantic-success">{uiStrings.cuentasEa.driftEmpty}</p>
        )}
        <ul className="space-y-1">
          {drifted.map((row) => (
            <li key={row.bot_id} className="text-sm text-semantic-danger">
              {interpolate(uiStrings.cuentasEa.driftRow, {
                botId: row.bot_id,
                magic: row.magic_number,
                expected: row.expected_mode,
                reported: row.reported_mode,
              })}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
