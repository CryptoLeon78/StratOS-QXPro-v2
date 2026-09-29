import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { API_BASE_URL, apiFetch, withAccountScope } from "@/api/client";
import { useAccountScopeStore } from "@/stores/accountScopeStore";
import { server } from "@/test/mocks/server";

afterEach(() => {
  useAccountScopeStore.setState({ selectedAccountId: null });
});

describe("withAccountScope", () => {
  it("no toca la ruta si no hay cuenta elegida", () => {
    expect(withAccountScope("/api/v1/bots")).toBe("/api/v1/bots");
  });

  it("anade account_id a las rutas /api/v1 con y sin query", () => {
    useAccountScopeStore.setState({ selectedAccountId: 4 });
    expect(withAccountScope("/api/v1/bots")).toBe("/api/v1/bots?account_id=4");
    expect(withAccountScope("/api/v1/summary/equity-curve?range=90d")).toBe(
      "/api/v1/summary/equity-curve?range=90d&account_id=4"
    );
  });

  it("respeta un account_id explicito y no toca rutas fuera de /api/v1", () => {
    useAccountScopeStore.setState({ selectedAccountId: 4 });
    expect(withAccountScope("/api/v1/bots?account_id=2")).toBe("/api/v1/bots?account_id=2");
    expect(withAccountScope("/auth/refresh")).toBe("/auth/refresh");
  });
});

describe("apiFetch con cuenta elegida", () => {
  it("envia account_id en la peticion real", async () => {
    let received: string | null = null;
    server.use(
      http.get(`${API_BASE_URL}/api/v1/bots`, ({ request }) => {
        received = new URL(request.url).searchParams.get("account_id");
        return HttpResponse.json([]);
      })
    );
    useAccountScopeStore.setState({ selectedAccountId: 2 });

    await apiFetch("/api/v1/bots");

    expect(received).toBe("2");
  });
});
