import { expect, test } from "@playwright/test";

import { EMAIL, PASSWORD, login } from "./helpers";

test.skip(!EMAIL || !PASSWORD, "PLAYWRIGHT_TEST_EMAIL/PLAYWRIGHT_TEST_PASSWORD no configurados");

// api/client.ts::API_BASE_URL -- la API vive en un origen DISTINTO del
// frontend (:8100 vs :5175/:5173), asi que las llamadas de page.request
// (que resuelve URLs relativas contra `baseURL` = el origen del FRONTEND)
// necesitan la URL absoluta del backend, no una ruta relativa.
const API_BASE_URL = process.env.VITE_API_BASE_URL ?? "http://localhost:8100";

// Flujo compuesto de G8: login -> confirmar una decision (UI real) ->
// firmar un item de checklist (API directa, PARTE 13: no existe UI de
// checklist todavia -- ver ASSUMPTIONS G8, backlog) -> registrar un
// impulso (UI real, ImpulseFormDialog, G7).
test("flujo operativo: confirmar decision, firmar checklist, registrar impulso", async ({
  page,
}) => {
  await login(page);

  // 1. Confirmar una decision pendiente desde Resumen. Poseidón Trend GER40
  // es quien realmente genera una Decision confirmable (bots_production.py:
  // el sweep real la avanza AMARILLO->NARANJA, requires_confirmation=True en
  // semaphore.py) -- Hipnos Grid US30 solo dispara un Alert de watchdog
  // (services/watchdog.py), nunca una Decision; usar su nombre aqui era un
  // error de este spec, corregido tras verlo fallar en CI real (G8).
  const poseidonCard = page.locator(".border-l-accent-primary").filter({ hasText: "Poseidón" });
  await expect(poseidonCard.getByRole("button", { name: "Confirmar" })).toBeVisible();
  await poseidonCard.getByRole("button", { name: "Confirmar" }).click();
  await expect(poseidonCard).toHaveCount(0);

  // 2. Firmar un item de checklist dominical -- sin UI (hallazgo real de
  // planificacion de G8, ASSUMPTIONS), vía la API real reutilizando la
  // sesión ya autenticada por la UI. `page.request` comparte cookies con
  // el browser context pero NO localStorage -- el auth de esta app es
  // JWT en localStorage (authStore, Zustand), asi que el Bearer hay que
  // adjuntarlo a mano, leido del propio localStorage ya autenticado.
  const accessToken = await page.evaluate(() => {
    // stores/authStore.ts: persist({ name: "stratos-auth" }).
    const raw = localStorage.getItem("stratos-auth");
    return raw ? JSON.parse(raw).state.accessToken : null;
  });
  const authHeaders = { Authorization: `Bearer ${accessToken}` };

  const before = await page.request.get(
    `${API_BASE_URL}/api/v1/checklists/current?checklist_type=SUNDAY`,
    { headers: authHeaders }
  );
  expect(before.ok()).toBeTruthy();
  const beforeBody = await before.json();
  const firstItem = beforeBody.items[0].item_key as string;

  const signResponse = await page.request.post(
    `${API_BASE_URL}/api/v1/checklists/SUNDAY/items/${encodeURIComponent(firstItem)}/sign`,
    { headers: authHeaders }
  );
  expect(signResponse.ok()).toBeTruthy();
  const signBody = await signResponse.json();
  const signedItem = signBody.progress.items.find(
    (i: { item_key: string; signed: boolean }) => i.item_key === firstItem
  );
  expect(signedItem.signed).toBe(true);

  // 3. Registrar un impulso desde Bots (ImpulseFormDialog, UI real).
  await page.goto("/bots");
  await page.getByText("Selene MeanRev XAG").first().click();
  await page.getByRole("button", { name: "Tengo el impulso de intervenir" }).click();
  await page
    .getByLabel("Descripción del impulso")
    .fill("Impulso de prueba E2E: quiero pausar tras ver una vela en contra.");
  await page.getByRole("button", { name: "Registrar impulso" }).click();
  await expect(
    page.getByText("Impulso registrado — se evaluará su contrafactual a 7 días.")
  ).toBeVisible();
});
