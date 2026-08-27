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

  // G9: AccountCard.tsx ahora reserva SIEMPRE la altura de la fila de
  // heartbeat/latencia/uptime (invisible en vez de ausente, ver el propio
  // componente) -- ya no desplaza la pagina, pero el TEXTO (timestamp real,
  // latencia, % de uptime) sigue variando entre corridas, asi que se
  // enmascara igual que el resto de contenido dinamico (headerMask).
  await expect(page).toHaveScreenshot("cuentas_ea.png", {
    maxDiffPixelRatio: 0.02,
    mask: [...headerMask(page), page.getByText(/^(Conectado|Desconectado)$/).locator("..")],
  });
});
