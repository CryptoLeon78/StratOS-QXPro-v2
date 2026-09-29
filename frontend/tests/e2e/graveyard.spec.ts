import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Graveyard: 9 lapidas, banner sin retorno, reactivar sin flujo de exito", async ({
  page,
}) => {
  await login(page);
  await page.goto("/graveyard");

  await expect(
    page.getByText("Un bot retirado nunca se reactiva sin re-validación completa")
  ).toBeVisible();
  await expect(page.getByText("9/9")).toBeVisible();
  await expect(page.getByText("Prometeo Trend EURUSD #117021")).toBeVisible();

  // Criterio 4 (PARTE 16): reactivar es siempre informativo (409 real),
  // nunca un flujo de exito -- el boton existe pero no hay confirmacion.
  await expect(page.getByRole("button", { name: "Reactivar" }).first()).toBeVisible();

  await page.waitForLoadState("networkidle");

  await expect(page).toHaveScreenshot("graveyard.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});
