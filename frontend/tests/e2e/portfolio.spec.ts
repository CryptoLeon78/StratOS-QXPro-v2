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
  // Criterio 9 (PARTE 16): media de correlacion ~0,16 (perfil full).
  await expect(page.getByText(/media 0[.,]1[5-7]/)).toBeVisible();

  await expect(page).toHaveScreenshot("portfolio.png", {
    maxDiffPixelRatio: 0.02,
    mask: [...headerMask(page), page.locator("table")],
  });
});
