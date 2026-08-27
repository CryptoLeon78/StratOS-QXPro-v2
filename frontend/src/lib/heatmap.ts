import tokens from "@/styles/tokens";

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  return [
    parseInt(clean.slice(0, 2), 16),
    parseInt(clean.slice(2, 4), 16),
    parseInt(clean.slice(4, 6), 16),
  ];
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function mixHex(fromHex: string, toHex: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(fromHex);
  const [r2, g2, b2] = hexToRgb(toHex);
  const r = Math.round(lerp(r1, r2, t));
  const g = Math.round(lerp(g1, g2, t));
  const b = Math.round(lerp(b1, b2, t));
  return `rgb(${r}, ${g}, ${b})`;
}

// tokens.color.heatmap: escala divergente min->mid->max (correlacion 0..1,
// PARTE 7.5) -- "correlacion alta = rojo intenso" (design_tokens.json).
export function correlationHeatmapColor(value: number): string {
  const clamped = Math.max(0, Math.min(1, value));
  const { min, mid, max } = tokens.color.heatmap;
  return clamped < 0.5 ? mixHex(min, mid, clamped * 2) : mixHex(mid, max, (clamped - 0.5) * 2);
}
