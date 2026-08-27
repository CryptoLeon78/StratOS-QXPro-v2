import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Riesgo: escalera kill-switch, tail risk, exposicion, news shield", async ({
  page,
}) => {
  await login(page);
  await page.goto("/riesgo");

  await expect(page.getByText("Drawdown y kill-switch")).toBeVisible();
  await expect(page.getByText("L1 · >8%")).toBeVisible();
  await expect(page.getByText("L4 · >20%")).toBeVisible();
  await expect(page.getByText("Tail Risk (VaR / CVaR, 60d)")).toBeVisible();
  await expect(page.getByText("News Shield")).toBeVisible();
  // Escenario sembrado: 2 noticias HIGH dentro de 48h (PARTE 13).
  await expect(page.getByText("IFO Business Climate")).toBeVisible();
  await expect(page.getByText("Durable Goods Orders")).toBeVisible();

  await expect(page).toHaveScreenshot("riesgo.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});
