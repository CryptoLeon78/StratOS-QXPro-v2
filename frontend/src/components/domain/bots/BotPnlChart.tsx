import { AreaSeries, createChart, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";

import tokens from "@/styles/tokens";
import type { PnlCurvePoint } from "@/api/endpoints/bots";

const RANGE_DAYS: Record<string, number | null> = {
  "30d": 30,
  "90d": 90,
  "180d": 180,
  all: null,
};

interface BotPnlChartProps {
  points: PnlCurvePoint[];
  range: string;
}

// Mismo patron que EquityAreaChart.tsx (PARTE 4: Lightweight Charts para
// equity/P&L) -- adaptado a PnlCurvePoint (G10, GET /bots/{id}/pnl-curve):
// el primer punto (arranque sintetico) trae ts=null, se excluye del chart
// (no hay fecha real que representarlo). Filtro de rango client-side --
// el endpoint no acepta `range`, a diferencia de /summary/equity-curve.
//
// Bug real encontrado en verificacion en vivo (no en tests): a diferencia
// de EquityAreaChart (1 punto por dia, fechas ya unicas), aqui cada punto
// es un trade cerrado -- varios trades el mismo dia truncados a "YYYY-MM-DD"
// producian timestamps duplicados y lightweight-charts exige orden
// ESTRICTAMENTE ascendente (rompia con "data must be asc ordered by time").
// Fix: UTCTimestamp (segundos Unix) con precision real de `close_time` en
// vez de truncar a dia.
export function BotPnlChart({ points, range }: BotPnlChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  // `now` capturado una vez por montaje (useState lazy-init), no recalculado
  // en cada render/memo -- eslint react-hooks/purity prohibe llamar
  // Date.now() directamente dentro de render o de un useMemo.
  const [now] = useState(() => Date.now());
  const filtered = useMemo(() => {
    const dated = points.filter(
      (p): p is PnlCurvePoint & { ts: string } => p.ts !== null
    );
    const days = RANGE_DAYS[range];
    if (days === null || days === undefined) return dated;
    const cutoff = now - days * 24 * 60 * 60 * 1000;
    return dated.filter((p) => new Date(p.ts).getTime() >= cutoff);
  }, [points, range, now]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
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
      timeScale: { borderColor: tokens.color.chart.grid, timeVisible: true, secondsVisible: false },
    });
    chartRef.current = chart;

    const series = chart.addSeries(AreaSeries, {
      lineColor: tokens.color.chart.equityLine,
      topColor: tokens.color.chart.equityArea,
      bottomColor: "rgba(34, 197, 94, 0)",
      lineWidth: 2,
      priceLineVisible: false,
    });
    // Segundos Unix con des-colision defensiva: si 2 trades cierran en el
    // mismo segundo exacto (raro, pero posible), lightweight-charts sigue
    // exigiendo orden ESTRICTAMENTE creciente -- se empuja +1s al punto
    // colisionado (los puntos ya vienen ordenados por close_time real).
    let lastTime = 0;
    const seriesData = filtered.map((p) => {
      let time = Math.floor(new Date(p.ts).getTime() / 1000);
      if (time <= lastTime) time = lastTime + 1;
      lastTime = time;
      return { time: time as UTCTimestamp, value: Number(p.cumulative_pnl) };
    });
    series.setData(seriesData);
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [filtered]);

  return <div ref={containerRef} className="h-64 w-full" />;
}
