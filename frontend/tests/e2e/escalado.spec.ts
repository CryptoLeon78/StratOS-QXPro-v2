import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Escalado: las 6 fases UMS", async ({ page }) => {
  await login(page);
  await page.goto("/escalado");

  await expect(page.getByText("Las 6 fases UMS")).toBeVisible();
  await expect(page.getByText(/1 . Validaci.n Personal/)).toBeVisible();
  await expect(page.getByText("6 · Institucional", { exact: false })).toBeVisible();

  // La fase UMS actual (por cuenta) llega de una peticion aparte: bajo carga en
  // paralelo la captura se tomaba antes de que pintara (fallo intermitente 1 de 3).
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveScreenshot("escalado.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});
