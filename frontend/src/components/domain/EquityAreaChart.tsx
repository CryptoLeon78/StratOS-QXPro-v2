import { AreaSeries, createChart, type IChartApi } from "lightweight-charts";
import { useEffect, useRef } from "react";

import tokens from "@/styles/tokens";

interface EquityAreaChartProps {
  points: { date: string; equity: number }[];
}

// PARTE 4: Lightweight Charts reservado para equity/P&L. date de
// EquityCurvePoint ya viene "YYYY-MM-DD" (header.py::equity_curve, str(date))
// -- coincide con el formato "business day string" que la libreria espera
// para `time`, sin conversion.
export function EquityAreaChart({ points }: EquityAreaChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: tokens.color.text.secondary,
      },
      grid: {
        vertLines: { color: tokens.color.chart.grid },
        horzLines: { color: tokens.color.chart.grid },
      },
      rightPriceScale: { borderColor: tokens.color.chart.grid },
      timeScale: { borderColor: tokens.color.chart.grid },
    });
    chartRef.current = chart;

    const series = chart.addSeries(AreaSeries, {
      lineColor: tokens.color.chart.equityLine,
      topColor: tokens.color.chart.equityArea,
      bottomColor: "rgba(34, 197, 94, 0)",
      lineWidth: 2,
      priceLineVisible: false,
    });
    series.setData(points.map((p) => ({ time: p.date, value: p.equity })));
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points]);

  return <div ref={containerRef} className="h-64 w-full" />;
}
