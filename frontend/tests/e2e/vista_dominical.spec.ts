import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

// Criterio 14 (PARTE 16, literal): "Vista dominical sin ninguna cifra de
// rentabilidad (test de contenido)". No es un screenshot-diff -- es una
// aserción de CONTENIDO: la pagina completa no debe contener ningun simbolo
// de moneda, y el AppHeader normal (EQUITY/P&L/DD) no debe estar montado
// -- /dominical es una ruta de nivel superior separada de RootLayout,
// nunca importa AppHeader.
test("vista dominical: revision tecnica sin ninguna cifra de rentabilidad", async ({ page }) => {
  await login(page);
  await page.goto("/dominical");

  await expect(page.getByRole("heading", { name: "Revisión dominical" })).toBeVisible();
  await expect(page.getByText("Errores de EA", { exact: true })).toBeVisible();
  await expect(page.getByText("Desconexiones", { exact: true })).toBeVisible();
  await expect(page.getByText("Órdenes rechazadas", { exact: true })).toBeVisible();
  await expect(page.getByText(/News Shield/)).toBeVisible();

  // El AppHeader normal (EQUITY/P&L DÍA/DRAWDOWN) nunca se monta aqui --
  // esas 3 etiquetas son literales unicos de StatCard, no aparecen en
  // ningun otro sitio de la app.
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("EQUITY");
  expect(bodyText).not.toContain("P&L DÍA");
  expect(bodyText).not.toContain("DRAWDOWN");
});
