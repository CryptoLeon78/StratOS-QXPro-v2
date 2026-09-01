import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAccountsDrift } from "@/hooks/queries/useAccounts";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.2 "Panel Deriva de configuracion": GET /accounts/drift, mapeo
// directo: modo operativo, permiso AutoTrading y sizing aplicado frente al
// sizing contractual. Un sizing ausente sigue siendo no comparable (no se
// presenta falsamente como conforme).
export function DriftPanel() {
  const { data } = useAccountsDrift();
  const drifted = (data ?? []).filter(
    (row) => row.drift || row.autotrading_drift || row.sizing_drift === true
  );

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
              {(row.autotrading_drift || row.sizing_drift === true) && (
                <span className="text-text-secondary">
                  {" "}
                  {interpolate(uiStrings.cuentasEa.driftOperationalDetails, {
                    expectedAutotrading: row.expected_autotrading ? "ON" : "OFF",
                    reportedAutotrading: row.reported_autotrading ? "ON" : "OFF",
                    expectedSizing: row.expected_sizing_pct,
                    reportedSizing: row.reported_sizing_pct ?? "—",
                  })}
                </span>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
