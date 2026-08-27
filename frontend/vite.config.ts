/// <reference types="vitest/config" />
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // G9: los 2 mayores contribuyentes al aviso de "chunk >500kB" de
        // Rollup desde G7 (docs/backlog.md) -- cada uno en su propio chunk,
        // separado del bundle principal y de las paginas lazy que los usan
        // (equity de Resumen/lightweight-charts, Portfolio/recharts).
        manualChunks: {
          "lightweight-charts": ["lightweight-charts"],
          recharts: ["recharts"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // tests/e2e/ es Playwright (otro test runner, otra API de test.*),
    // no Vitest -- excluir para que no se ejecuten como si fueran uno.
    exclude: ["node_modules/**", "tests/e2e/**"],
  },
});
