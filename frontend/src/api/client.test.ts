import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { apiFetch, API_BASE_URL, ApiError } from "@/api/client";
import { server } from "@/test/mocks/server";
import { useAuthStore } from "@/stores/authStore";

beforeEach(() => {
  useAuthStore.getState().clear();
});

describe("apiFetch", () => {
  it("adjunta el Authorization: Bearer del store", async () => {
    useAuthStore.getState().setSession("token-abc", "refresh-abc");
    let receivedAuth: string | null = null;
    server.use(
      http.get(`${API_BASE_URL}/api/v1/probe`, ({ request }) => {
        receivedAuth = request.headers.get("Authorization");
        return HttpResponse.json({ ok: true });
      })
    );

    await apiFetch("/api/v1/probe");

    expect(receivedAuth).toBe("Bearer token-abc");
  });

  it("en un 401 refresca una sola vez aunque varias peticiones fallen a la vez, y reintenta con el token nuevo", async () => {
    useAuthStore.getState().setSession("token-stale", "refresh-abc");
    let refreshCalls = 0;
    server.use(
      http.post(`${API_BASE_URL}/auth/refresh`, () => {
        refreshCalls += 1;
        return HttpResponse.json({
          access_token: "token-fresh",
          refresh_token: "refresh-fresh",
          token_type: "bearer",
          expires_in: 900,
        });
      }),
      http.get(`${API_BASE_URL}/api/v1/probe`, ({ request }) => {
        const auth = request.headers.get("Authorization");
        if (auth === "Bearer token-fresh") {
          return HttpResponse.json({ ok: true });
        }
        return new HttpResponse(null, { status: 401 });
      })
    );

    const results = await Promise.all([
      apiFetch("/api/v1/probe"),
      apiFetch("/api/v1/probe"),
      apiFetch("/api/v1/probe"),
    ]);

    expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
    expect(refreshCalls).toBe(1);
    expect(useAuthStore.getState().accessToken).toBe("token-fresh");
  });

  it("si el refresh tambien falla, limpia la sesion y lanza ApiError", async () => {
    useAuthStore.getState().setSession("token-stale", "refresh-dead");
    server.use(
      http.post(`${API_BASE_URL}/auth/refresh`, () => new HttpResponse(null, { status: 401 })),
      http.get(`${API_BASE_URL}/api/v1/probe`, () => new HttpResponse(null, { status: 401 }))
    );

    await expect(apiFetch("/api/v1/probe")).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
