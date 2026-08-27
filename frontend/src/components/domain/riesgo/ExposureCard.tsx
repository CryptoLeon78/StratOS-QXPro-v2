import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExposure } from "@/hooks/queries/useRisk";
import { formatSignedAmount } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.7 "Exposicion en vivo": GET /risk/exposure, agregado solo por
// simbolo (unidad nativa, sin conversion de divisa -- gap ya documentado
// en G5/docs/backlog.md). Los subtotales por divisa de la captura ("BTC:
// +0.46  USD: +2.33") no estan en ExposureRowResponse (no tiene campo de
// divisa) -- se omiten.
export function ExposureCard() {
  const { data } = useExposure();

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
      </CardContent>
    </Card>
  );
}
