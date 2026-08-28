import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, XAxis, YAxis } from "recharts";

import tokens from "@/styles/tokens";

const BUCKET_WIDTH_R = 0.5;

interface RMultipleHistogramProps {
  values: string[];
}

// "Histograma de retornos (R)" (7.4) -- agrupa los R-multiples reales
// (GET /bots/{id}/r-multiples, G10) en buckets de 0.5R para el BarChart.
// El ancho de bucket es una decision de presentacion (cuantos bins caben
// legibles en el ancho del panel), no un umbral de negocio -- mismo
// criterio que el layout="vertical" de MacroStructureCard.tsx.
export function RMultipleHistogram({ values }: RMultipleHistogramProps) {
  const buckets = useMemo(() => {
    const nums = values.map(Number);
    const counts = new Map<number, number>();
    for (const r of nums) {
      const bucket = Math.round(r / BUCKET_WIDTH_R) * BUCKET_WIDTH_R;
      counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
    }
    return [...counts.entries()]
      .sort(([a], [b]) => a - b)
      .map(([bucket, count]) => ({ label: bucket.toFixed(1), count }));
  }, [values]);

  if (buckets.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={buckets} margin={{ left: -20 }}>
        <CartesianGrid vertical={false} stroke={tokens.color.chart.grid} />
        <XAxis dataKey="label" stroke={tokens.color.chart.axis} tick={{ fontSize: 10 }} />
        <YAxis
          allowDecimals={false}
          stroke={tokens.color.chart.axis}
          tick={{ fontSize: 10 }}
        />
        <Bar dataKey="count" fill={tokens.color.accent.primary} radius={2} />
      </BarChart>
    </ResponsiveContainer>
  );
}
