import { describe, expect, it } from "vitest";

import { computeMaxDrawdownPct } from "@/lib/equityStats";

describe("computeMaxDrawdownPct", () => {
  it("curva vacia -> 0", () => {
    expect(computeMaxDrawdownPct([])).toBe(0);
  });

  it("curva siempre subiendo -> 0", () => {
    expect(computeMaxDrawdownPct([100, 110, 120, 130])).toBe(0);
  });

  it("pico y caida simple -> % correcto", () => {
    // pico 200, valle 180 -> (200-180)/200*100 = 10%
    expect(computeMaxDrawdownPct([100, 200, 180])).toBeCloseTo(10);
  });

  it("varias caidas -> se queda con la peor", () => {
    // pico 100 -> 90 (10%) ; pico 150 -> 120 (20%)
    expect(computeMaxDrawdownPct([100, 90, 150, 120])).toBeCloseTo(20);
  });
});
