import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { attemptReactivation } from "@/api/endpoints/cemetery";
import { server } from "@/test/mocks/server";

// PARTE 6.3 "API 409 siempre; sin control en UI" -- evaluate_cemetery_
// reactivation esta disenada para rechazar SIEMPRE. Este test confirma que
// el wrapper del frontend nunca trata un 409 como excepcion no controlada:
// devuelve el motivo como string, y solo re-lanza si (nunca deberia
// pasar) el backend devolviera 200.
describe("attemptReactivation", () => {
  it("devuelve el motivo del 409 como string, no lanza", async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/v1/cemetery/42/reactivate`, () =>
        HttpResponse.json(
          { detail: "Un bot retirado nunca se reactiva sin re-validación completa (pipeline desde Fase 3)." },
          { status: 409 }
        )
      )
    );

    const reason = await attemptReactivation(42);

    expect(reason).toBe(
      "Un bot retirado nunca se reactiva sin re-validación completa (pipeline desde Fase 3)."
    );
  });

  it("relanza si (nunca deberia pasar) el backend responde 200", async () => {
    server.use(
      http.post(`${API_BASE_URL}/api/v1/cemetery/42/reactivate`, () => HttpResponse.json({}))
    );

    await expect(attemptReactivation(42)).rejects.toThrow();
  });
});
