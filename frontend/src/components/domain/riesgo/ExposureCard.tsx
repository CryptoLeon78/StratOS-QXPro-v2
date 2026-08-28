import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExposure, useExposureByCurrency } from "@/hooks/queries/useRisk";
import { formatSignedAmount } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.7 "Exposicion en vivo": GET /risk/exposure, agregado por simbolo
// (unidad nativa). Subtotales por divisa ("BTC: +0.46  USD: +2.33") desde
// G10: GET /risk/exposure/by-currency (unidad nativa, NO conversion a EUR
// -- ese endpoint separado, /risk/exposure/eur, no se consume aqui porque
// la captura muestra montos en la divisa propia de cada posicion, no EUR).
export function ExposureCard() {
  const { data } = useExposure();
  const { data: byCurrency } = useExposureByCurrency();

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {interpolate(uiStrings.riesgo.exposureTitle, { count: (data ?? []).length })}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <tbody>
            {(data ?? []).map((row) => (
              <tr key={row.symbol} className="border-t border-border-subtle first:border-t-0">
                <td className="py-1.5 font-medium text-text-primary">{row.symbol}</td>
                <td
                  className={`py-1.5 text-right ${Number(row.net_volume) >= 0 ? "text-pnl-positive" : "text-pnl-negative"}`}
                >
                  {formatSignedAmount(row.net_volume)}
                </td>
                <td className="py-1.5 text-right text-text-secondary">{row.gross_volume}</td>
                <td
                  className={`py-1.5 text-right ${Number(row.pnl) >= 0 ? "text-pnl-positive" : "text-pnl-negative"}`}
                >
                  {formatSignedAmount(row.pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(byCurrency ?? []).length > 0 && (
          <p className="mt-2 text-xs text-text-secondary">
            {(byCurrency ?? [])
              .map(
                (row) =>
                  `${row.currency}: ${formatSignedAmount(row.net_volume)}`
              )
              .join("  ")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
