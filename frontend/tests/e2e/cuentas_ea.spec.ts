import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Cuentas/EA: Prod + Quarry, deriva de configuracion, panel TCA pendiente", async ({
  page,
}) => {
  await login(page);
  await page.goto("/cuentas-ea");

  await expect(page.getByText("Prod", { exact: true })).toBeVisible();
  await expect(page.getByText("Quarry", { exact: true })).toBeVisible();
  await expect(page.getByText("stratos-prod-1")).toBeVisible();
  await expect(page.getByText("stratos-quarry-1")).toBeVisible();
  await expect(page.getByText("Deriva de configuración")).toBeVisible();
  await expect(page.getByText("Sin deriva detectada")).toBeVisible();

  await expect(page).toHaveScreenshot("cuentas_ea.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});
