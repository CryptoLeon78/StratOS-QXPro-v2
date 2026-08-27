import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Pipeline: kanban F1-F7, Sigma GO, Estige HOLD, F4+ sin boton Promover", async ({
  page,
}) => {
  await login(page);
  await page.goto("/pipeline");

  await expect(page.getByText("F1 · Ideación y prototipado")).toBeVisible();
  await expect(page.getByText("F5 · Incubación OOS")).toBeVisible();

  // Cada candidato vive en su propio Card (.shadow-card, components/ui/card.tsx)
  // -- filtrar por texto lo escopea sin depender de la posicion en el DOM.
  const sigmaCard = page.locator(".shadow-card").filter({ hasText: "Sigma MeanRev SPX" });
  await expect(sigmaCard.getByText("GO", { exact: true })).toBeVisible();

  const estigeCard = page.locator(".shadow-card").filter({ hasText: "Estige Trend GBPUSD" });
  await expect(estigeCard.getByText("HOLD", { exact: true })).toBeVisible();

  // Criterio 10 (PARTE 16): F4+ nunca se promueve manualmente -- ni boton.
  const cefiroCard = page.locator(".shadow-card").filter({ hasText: "Cefiro MeanRev XAU" });
  await expect(cefiroCard.getByRole("button", { name: /Promover/ })).toHaveCount(0);

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
