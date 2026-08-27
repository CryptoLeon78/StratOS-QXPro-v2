import { expect, test } from "@playwright/test";

// Requiere PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD de un usuario
// real en el core-engine que este corriendo (no se hardcodea ninguna
// credencial, ni siquiera de dev, en el repo). Login via UI real (no
// inyectando el token a mano en localStorage): mas simple y robusto
// frente al formato interno de persistencia de Zustand, que no es un
// contrato estable a replicar en el test.
const EMAIL = process.env.PLAYWRIGHT_TEST_EMAIL;
const PASSWORD = process.env.PLAYWRIGHT_TEST_PASSWORD;

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Resumen: cabecera visible <2s, screenshot-diff dentro de umbral", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Correo").fill(EMAIL!);
  await page.getByLabel("Contraseña").fill(PASSWORD!);
  await page.getByRole("button", { name: "Entrar" }).click();

  // Criterio de salida literal de G6: "cabecera <2 s".
  await expect(page.getByText("EQUITY", { exact: true })).toBeVisible({ timeout: 2000 });
  await expect(page.getByText("Equity del portfolio (todos los bots)")).toBeVisible();
  await expect(page.getByText("Requiere acción")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pipeline", exact: true })).toBeVisible();

  await expect(page).toHaveScreenshot("resumen.png", {
    maxDiffPixelRatio: 0.02, // screenshot_similarity_max_diff_ratio, thresholds.seed.json
    mask: [
      // Numeros dinamicos (equity/PnL/fechas del chart) -- el diff valida
      // layout/estructura, no contenido variable (PARTE 11.1, mismo
      // criterio que el screenshot-diff de G7/G8).
      page.locator("header .grid"),
    ],
  });
});
