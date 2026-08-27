import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.10/7.2: TCA y Broker Profile dependen de la v1.1 del EA reporter
// (slippage + spread por ejecucion), que todavia no existe (PARTE 9.1: "sin
// consumidor aun" para /ingest/execution) -- esto NO es un hueco a
// disimular, es el propio estado "pendiente" que ya describe la captura
// literalmente. Reutilizado en Ejecucion y Cuentas/EA.
export function TcaPendingCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{uiStrings.ejecucion.tcaTitle}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-text-secondary">{uiStrings.ejecucion.tcaPending}</p>
        <p className="text-xs text-text-muted">{uiStrings.ejecucion.tcaPendingDetail}</p>
      </CardContent>
    </Card>
  );
}
