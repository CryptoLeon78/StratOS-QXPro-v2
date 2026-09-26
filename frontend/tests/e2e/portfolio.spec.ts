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

  // La matriz se presenta por procedencia: teorica (Strategy Tester) y
  // observada (MT5 real). Ambas cabeceras deben estar, sea cual sea su estado.
  await expect(page.getByText("Teórica · MT5 Strategy Tester")).toBeVisible();
  await expect(page.getByText("Observada · MT5 real (BEPB/JJTI)")).toBeVisible();

  // La fuente observada solo se calcula sobre cuentas BROKER_REAL -- "fixture
  // y demo no se consultan ni siquiera como relleno de serie"
  // (services/correlations.py). El seed es FIXTURE, asi que aqui se retiene
  // por diseño y no hay media que mostrar. Lo que se exige es que el panel
  // DECLARE su estado en vez de quedarse en blanco: una media real, o el
  // motivo de la retencion.
  await expect(
    page.getByText(/media 0[.,]\d\d|Snapshot retenido|Aún no existe un snapshot sellado/).first(),
  ).toBeVisible();

  await expect(page).toHaveScreenshot("portfolio.png", {
    maxDiffPixelRatio: 0.02,
    mask: [...headerMask(page), page.locator("table")],
  });
});
