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
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // tests/e2e/ es Playwright (otro test runner, otra API de test.*),
    // no Vitest -- excluir para que no se ejecuten como si fueran uno.
    exclude: ["node_modules/**", "tests/e2e/**"],
  },
});
