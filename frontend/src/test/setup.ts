import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "@/test/mocks/server";

// jsdom no implementa matchMedia (limitacion conocida, no especifica de
// ningun componente) -- lightweight-charts (EquityAreaChart) lo necesita
// para su Observable de device-pixel-ratio. Shim minimo estandar.
window.matchMedia ??= (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
});

// jsdom tampoco implementa HTMLCanvasElement.getContext (necesita el
// paquete nativo "canvas") -- lightweight-charts dibuja de verdad via
// requestAnimationFrame, y sin un contexto no-null lanza al medir el
// price axis. Stub minimo de los metodos que toca (no un mock de canvas
// completo -- solo evita el `ensureNotNull` interno).
const canvasContextStub = {
  fillRect: () => {},
  clearRect: () => {},
  getImageData: () => ({ data: [] }),
  putImageData: () => {},
  createImageData: () => [],
  setTransform: () => {},
  drawImage: () => {},
  save: () => {},
  restore: () => {},
  beginPath: () => {},
  moveTo: () => {},
  lineTo: () => {},
  closePath: () => {},
  stroke: () => {},
  fill: () => {},
  arc: () => {},
  rect: () => {},
  clip: () => {},
  translate: () => {},
  scale: () => {},
  rotate: () => {},
  transform: () => {},
  fillText: () => {},
  strokeText: () => {},
  measureText: () => ({ width: 0 }),
  createLinearGradient: () => ({ addColorStop: () => {} }),
};
// jsdom SI define getContext (a diferencia de matchMedia) pero devuelve
// null y avisa "Not implemented" -- hace falta sobreescribirla siempre,
// ??= no basta porque la propiedad ya existe.
// @ts-expect-error -- stub deliberadamente parcial, no un CanvasRenderingContext2D real
HTMLCanvasElement.prototype.getContext = () => canvasContextStub;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  // globals:false en vite.config.ts -- @testing-library/react no detecta un
  // afterEach global automatico para su cleanup, hay que registrarlo aqui.
  cleanup();
});
afterAll(() => server.close());
