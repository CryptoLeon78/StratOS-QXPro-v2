import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, headerMask, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

test("pestana Auditoria: reconciliacion limpia, continuidad, sellos de integridad", async ({
  page,
}) => {
  await login(page);
  await page.goto("/auditoria");

  await expect(page.getByText("Reconciliación contable")).toBeVisible();
  // Criterio 6 (PARTE 16): seed limpio -> descuadre 0,0% (sin --inject-audit-error).
  await expect(page.getByText("Descuadre")).toBeVisible();
  await expect(page.getByText("0,0%").first()).toBeVisible();
  await expect(page.getByText("Continuidad del envío (7 días)")).toBeVisible();
  await expect(page.getByText("Sellos de integridad")).toBeVisible();
  await expect(page.getByText("LOTES SELLADOS (HASH+TS)")).toBeVisible();
  await expect(
    page.getByText("NO constituye una auditoría contable, financiera ni legal")
  ).toBeVisible();

  await expect(page).toHaveScreenshot("auditoria.png", {
    maxDiffPixelRatio: 0.02,
    mask: headerMask(page),
  });
});
