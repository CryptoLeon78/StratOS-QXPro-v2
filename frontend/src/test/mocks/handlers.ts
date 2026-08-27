import { http, HttpResponse } from "msw";

import { API_BASE_URL } from "@/api/client";

export const handlers = [
  http.post(`${API_BASE_URL}/auth/token`, async ({ request }) => {
    const body = await request.text();
    const params = new URLSearchParams(body);
    if (params.get("username") === "operator@stratos.local" && params.get("password") === "ok") {
      return HttpResponse.json({
        access_token: "fake.access.token",
        refresh_token: "fake.refresh.token",
        token_type: "bearer",
        expires_in: 900,
      });
    }
    return new HttpResponse(null, { status: 401 });
  }),

  http.post(`${API_BASE_URL}/auth/refresh`, () =>
    HttpResponse.json({
      access_token: "refreshed.access.token",
      refresh_token: "refreshed.refresh.token",
      token_type: "bearer",
      expires_in: 900,
    })
  ),
];
