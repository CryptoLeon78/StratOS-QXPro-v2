import type { Page } from "@playwright/test";

// Compartido entre todos los specs de G8 -- mismo patron de login real por
// UI que resumen.spec.ts (G6), nunca credenciales hardcodeadas ni inyeccion
// de token en localStorage (formato interno de Zustand no es un contrato
// estable a replicar en un test).
export const EMAIL = process.env.PLAYWRIGHT_TEST_EMAIL;
export const PASSWORD = process.env.PLAYWRIGHT_TEST_PASSWORD;

export async function login(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Correo").fill(EMAIL!);
  await page.getByLabel("Contraseña").fill(PASSWORD!);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("**/");
}

// Mascara de la cabecera global (persistente en las 11 pestañas): equity,
// P&L, DD, badge STALE -- todos numeros/fechas dinamicos que cambian entre
// corridas del seed. El screenshot-diff valida layout/estructura, no
// contenido variable (mismo criterio que resumen.spec.ts, G6).
//
// Bug real encontrado en G10 (CI run 33124859460): el badge STALE vivia
// FUERA de "header .grid" (es un <div> hermano, no un hijo del grid de
// StatCard) -- el comentario de arriba ya documentaba la intencion de
// enmascararlo, pero el selector nunca lo cubrio. `data_stale_seconds`
// depende del reloj real (gap entre el heartbeat sembrado y el momento
// exacto de la corrida), asi que el texto ("hace N min") variaba entre
// corridas y metia pixeles reales de diff fuera de mascara -- suficiente
// para cruzar el 2% una vez que las 4 chips nuevas de Salud (m-01)
// redujeron el margen que quedaba libre.
export function headerMask(page: Page) {
  return [page.locator("header .grid"), page.getByTestId("data-stale-badge")];
}
