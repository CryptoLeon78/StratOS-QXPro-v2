import { defineConfig, devices } from "@playwright/test";

// Spec minimo deliberado (un solo archivo, un solo proyecto) -- el
// harness completo de 11 pestanas es G8 ("Seed + E2E", PARTE 12). Este
// spec se reutiliza como base en G7/G8, no se reescribe.
//
// Necesita core-engine real corriendo en VITE_API_BASE_URL (por defecto
// http://localhost:8100) con un usuario valido -- no hay mock de red
// aqui (MSW es solo para Vitest/jsdom). No wireado en CI todavia: el job
// `lint-and-build-frontend` no levanta Postgres/Redis/core-engine: eso
// es tarea de G8 (build de scripts/seed.py + el harness E2E completo).
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5175",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
