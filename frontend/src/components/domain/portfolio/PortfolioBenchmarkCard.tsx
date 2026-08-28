import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePortfolioBenchmark } from "@/hooks/queries/usePortfolio";
import { formatPercent } from "@/lib/formatters";
import tokens from "@/styles/tokens";
import uiStrings from "@/styles/ui_strings.es.json";

function fmt2(value: number): string {
  return value.toFixed(2);
}

// PARTE 7.3 "¿Añade valor real el portfolio?" (G10, seccion sin captura de
// referencia en "pestaña Portfolio.jpg" -- esta en la captura separada
// "seccion_de_pestaña_portfolio_que_no_se_ve_en_imagen..."). Consume
// GET /portfolio/benchmark (services/benchmark.py, G10). Reusa los 2
// colores de linea YA declarados en design_tokens.json (equityLine/
// botPnlLine) en vez de inventar los tonos purpura/cian exactos de la
// captura -- doc_app/ es contractual, no se toca.
//
// Convenciones de unidad del backend, verificadas contra el codigo real
// (no asumidas): cagr_portfolio/cagr_benchmark/batting_average ya vienen
// en escala porcentual (*100 aplicado server-side); alpha es una fraccion
// mensual cruda (necesita *100 para "1.41%"); beta/t_stat/information_ratio
// son ratios/estadisticos sin unidad; up_capture/down_capture ya vienen
// en escala porcentual pero la captura los muestra como ratio decimal
// (0.69, no 69%) -- se dividen /100 solo para el display, sin tocar el
// dato real.
export function PortfolioBenchmarkCard() {
  const { data } = usePortfolioBenchmark();

  const chartData = (data?.monthly_points ?? []).map((p) => ({
    date: p.date,
    Portfolio: p.portfolio_return * 100,
    "S&P 500": p.benchmark_return * 100,
  }));

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <CardTitle>{uiStrings.portfolio.benchmarkTitle}</CardTitle>
          <span className="rounded-md bg-bg-surfaceHover px-2 py-0.5 text-xs text-text-secondary">
            {uiStrings.portfolio.benchmarkSelector}
          </span>
        </div>
        {data && (
          <Badge variant={data.alpha > 0 ? "success" : "danger"}>
            {data.alpha > 0
              ? uiStrings.portfolio.benchmarkAddsValue
              : uiStrings.portfolio.benchmarkNoValue}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {!data ? (
          <p className="text-sm text-text-secondary">{uiStrings.portfolio.benchmarkEmpty}</p>
        ) : (
          <>
            <dl className="grid grid-cols-4 gap-x-3 gap-y-3 text-xs sm:grid-cols-8">
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colPortfolioCagr}</dt>
                <dd className="font-semibold text-text-primary">
                  {formatPercent(data.cagr_portfolio)}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colBenchmarkCagr}</dt>
                <dd className="font-semibold text-text-primary">
                  {formatPercent(data.cagr_benchmark)}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colBeta}</dt>
                <dd className="font-semibold text-text-primary">{fmt2(data.beta)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colAlphaJensen}</dt>
                <dd className="font-semibold text-text-primary">
                  {formatPercent(data.alpha * 100)}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colTStatAlpha}</dt>
                <dd className="font-semibold text-text-primary">{fmt2(data.t_stat)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colInformationRatio}</dt>
                <dd className="font-semibold text-text-primary">{fmt2(data.information_ratio)}</dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colBattingAvg}</dt>
                <dd className="font-semibold text-text-primary">
                  {formatPercent(data.batting_average)}
                </dd>
              </div>
              <div>
                <dt className="text-text-secondary">{uiStrings.portfolio.colUpDownCapture}</dt>
                <dd className="font-semibold text-text-primary">
                  {data.up_capture === null ? "—" : fmt2(data.up_capture / 100)} /{" "}
                  {data.down_capture === null ? "—" : fmt2(data.down_capture / 100)}
                </dd>
              </div>
            </dl>

            {chartData.length > 0 && (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid stroke={tokens.color.chart.grid} />
                  <XAxis dataKey="date" stroke={tokens.color.chart.axis} tick={{ fontSize: 10 }} />
                  <YAxis stroke={tokens.color.chart.axis} tick={{ fontSize: 10 }} />
                  <Legend
                    formatter={(value) =>
                      value === "Portfolio"
                        ? uiStrings.portfolio.legendPortfolio
                        : uiStrings.portfolio.legendBenchmark
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="Portfolio"
                    stroke={tokens.color.chart.botPnlLine}
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="S&P 500"
                    stroke={tokens.color.chart.equityLine}
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
            <p className="text-xs text-text-muted">{uiStrings.portfolio.benchmarkSource}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
