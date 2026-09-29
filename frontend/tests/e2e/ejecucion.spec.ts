import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Ejecución: heartbeat, watchdog (Atlas OK), panel TCA pendiente", async ({
  page,
}) => {
  await login(page);
  await page.goto("/ejecucion");

  await expect(page.getByText("Heartbeat", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Watchdog de bots (frecuencia observada vs esperada, 30 días)")
  ).toBeVisible();
  // Criterio 7 (PARTE 16): Atlas 7 esperados/7 observados -> OK.
  const atlasRow = page.locator("tr").filter({ hasText: "Atlas Trend EURUSD" });
  await expect(atlasRow.getByText("OK", { exact: true })).toBeVisible();
  await expect(page.getByText("requieren la v1.1 del EA reporter")).toBeVisible();

  await page.waitForLoadState("networkidle");

  await expect(page).toHaveScreenshot("ejecucion.png", {
    maxDiffPixelRatio: 0.02,
    mask: [...headerMask(page), page.locator("table")],
  });
});
