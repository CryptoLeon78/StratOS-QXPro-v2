// Formato es-ES (PARTE 10.1: TZ_DISPLAY=Europe/Madrid, BASE_CURRENCY=EUR) --
// coma decimal, punto de millar, tal cual las capturas (179.642,70).
// `useGrouping: "always"` a proposito: el es-ES por defecto de Intl NO
// agrupa numeros de 4 cifras (2444,14 en vez de 2.444,14, verificado en
// Node 22) pero la captura de Resumen SI lo hace ("Sem: 2.444,14"), asi
// que se fuerza el agrupado en todos los tamanos.
const numberFormatter = new Intl.NumberFormat("es-ES", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  useGrouping: "always",
});

const signedNumberFormatter = new Intl.NumberFormat("es-ES", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  useGrouping: "always",
  signDisplay: "always",
});

const percentFormatter = new Intl.NumberFormat("es-ES", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatAmount(value: number | string): string {
  return numberFormatter.format(Number(value));
}

export function formatSignedAmount(value: number | string): string {
  return signedNumberFormatter.format(Number(value));
}

export function formatPercent(value: number | string): string {
  return `${percentFormatter.format(Number(value))}%`;
}
