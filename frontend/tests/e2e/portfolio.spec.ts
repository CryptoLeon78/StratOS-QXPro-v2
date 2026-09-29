import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Portfolio: estructura macro 40/40/20, 6 perfiles, benchmark", async ({
  page,
}) => {
  await login(page);
  await page.goto("/portfolio");

  await expect(page.getByText("Estructura macro 40/40/20")).toBeVisible();
  await expect(page.getByText("Los 6 perfiles (micro)")).toBeVisible();

  await expect(page).toHaveScreenshot("portfolio.png", {
    maxDiffPixelRatio: 0.02,
    mask: [...headerMask(page), page.locator("table")],
  });
});
