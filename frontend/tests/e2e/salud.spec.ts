import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Salud: grid de 32 tarjetas con semaforo e instruccion", async ({ page }) => {
  await login(page);
  await page.goto("/salud");

  await expect(page.getByText("Vega Grid GBPUSD")).toBeVisible();
  // La instruccion AMARILLO se repite por cada bot degradado (~28) -- .first().
  await expect(
    page
      .getByText("Reducir sizing al 50% (bajar fraction Kelly). Aumentar frecuencia de revisión.")
      .first()
  ).toBeVisible();

  await expect(page).toHaveScreenshot("salud.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});
