import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Portfolio: estructura macro 40/40/20, 6 perfiles, matriz de correlaciones", async ({
  page,
}) => {
  await login(page);
  await page.goto("/portfolio");

  await expect(page.getByText("Estructura macro 40/40/20")).toBeVisible();
  await expect(page.getByText("Los 6 perfiles (micro)")).toBeVisible();
  await expect(page.getByText("Matriz de correlaciones")).toBeVisible();
  // La calibracion a ~0,16 (PARTE 16) solo aplica al seed --profile full
  // (ver trades_history.py); este spec corre contra --profile ci, que no la
  // reproduce. Aqui solo se comprueba que el panel renderiza una media real.
  await expect(page.getByText(/media 0[.,]\d\d/)).toBeVisible();

  await expect(page).toHaveScreenshot("portfolio.png", {
    maxDiffPixelRatio: 0.02,
    mask: [...headerMask(page), page.locator("table")],
  });
});
