// Espejo en TS de core/formulas/trading.py::max_drawdown_pct -- calculo de
// presentacion sobre datos YA fetcheados del backend (no logica de dominio
// nueva). EquityCurvePoint no trae DD por punto (header.py::EquityCurvePoint
// solo sirve {date, equity}), asi que "DD max. periodo" de la captura de
// Resumen se deriva aqui, cliente, sobre el array del rango seleccionado.
export function computeMaxDrawdownPct(equityCurve: number[]): number {
  if (equityCurve.length === 0) {
    return 0;
  }
  let peak = equityCurve[0];
  let maxDd = 0;
  for (const value of equityCurve) {
    peak = Math.max(peak, value);
    if (peak > 0) {
      const drawdown = ((peak - value) / peak) * 100;
      maxDd = Math.max(maxDd, drawdown);
    }
  }
  return maxDd;
}
