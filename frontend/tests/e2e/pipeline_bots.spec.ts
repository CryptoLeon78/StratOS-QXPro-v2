import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Pipeline: tres carriles de Incubadora y portfolios reales read-only", async ({
  page,
}) => {
  await login(page);
  await page.goto("/pipeline");

  // ADR 0012: el operador retira F1-F3 de la superficie Pipeline. El tablero
  // ya no es el kanban F1-F7 -- gobierna la Incubadora demo y observa los dos
  // portfolios reales registrados. Este spec valida esa decision, no la UI
  // anterior.
  await expect(page.getByText("Incubadora demo → propuesta para portfolios reales")).toBeVisible();
  await expect(page.getByText("Orquestador de Incubadora")).toBeVisible();

  for (const carril of [
    "Instalación demo",
    "Observación contractual",
    "Evaluación de cartera",
  ]) {
    await expect(page.getByText(carril, { exact: false }).first()).toBeVisible();
  }

  // "Las tarjetas permanecen read-only: no existe una ruta de comando, sizing
  // o despliegue para BEPB/JJTI" (ADR 0012). Se comprueba la ausencia, que es
  // justo lo que la decision promete.
  await expect(page.getByRole("button", { name: /Promover|Desplegar|Instalar en real/ })).toHaveCount(0);

  await expect(page).toHaveScreenshot("pipeline.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});

test("pestana Bots: maestro-detalle, 32 en F7, impulso de intervenir disponible", async ({
  page,
}) => {
  await login(page);
  await page.goto("/bots");

  await expect(page.getByText("F7 (32)")).toBeVisible();
  await expect(page.getByText("Poseidón Trend GER40")).toBeVisible();

  // "Atlas Trend EURUSD" aparece 2 veces (fila de lista + cabecera del
  // detalle una vez seleccionado) -- .first() es la fila clicable.
  await page.getByText("Atlas Trend EURUSD").first().click();
  await expect(page.getByRole("button", { name: "Tengo el impulso de intervenir" })).toBeVisible();

  await expect(page).toHaveScreenshot("bots.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});
