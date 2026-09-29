import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Correlacion: dos matrices de la cuenta activa, con su estado declarado", async ({
  page,
}) => {
  await login(page);
  await page.goto("/correlacion");

  await expect(page.getByText("Matriz de correlaciones")).toBeVisible();

  // ADR 0013: teorica (Strategy Tester) y observada (MT5 real), cada una con el
  // nombre de la cuenta activa.
  await expect(page.getByText("Teórica · MT5 Strategy Tester · Prod")).toBeVisible();
  await expect(page.getByText("Observada · MT5 real · Prod")).toBeVisible();

  // Sea cual sea el estado, el panel lo DECLARA en vez de quedarse en blanco: una
  // media real, el motivo de la retencion o la ausencia de snapshot.
  await expect(
    page.getByText(/media 0[.,]\d\d|Snapshot retenido|Aún no existe un snapshot sellado/).first(),
  ).toBeVisible();

  await expect(page).toHaveScreenshot("correlacion.png", {
    maxDiffPixelRatio: 0.02,
    mask: [...headerMask(page), page.locator("table")],
  });
});
