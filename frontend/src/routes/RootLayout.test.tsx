import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import RootLayout from "@/routes/RootLayout";
import { useAccountScopeStore } from "@/stores/accountScopeStore";
import { useAuthStore } from "@/stores/authStore";
import { server } from "@/test/mocks/server";

// header claims={sub:"1",email:"dev@stratos.local",role:"operator",exp:9999999999}
const FAKE_ACCESS_TOKEN =
  "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJkZXZAc3RyYXRvcy5sb2NhbCIsInJvbGUiOiJvcGVyYXRvciIsImV4cCI6OTk5OTk5OTk5OX0.fake";

function mockBackend() {
  server.use(
    http.get(`${API_BASE_URL}/api/v1/accounts`, () =>
      HttpResponse.json([
        {
          id: 1,
          name: "BEPB",
          broker: "Darwinex",
          login: "1",
          server: "s",
          currency: "EUR",
          is_demo: false,
          data_origin: "BROKER_REAL",
          is_active: true,
          equity: "1000",
          balance: "1000",
          free_margin: null,
          margin_level: null,
          equity_ts: null,
          bot_count: 3,
        },
      ])
    ),
    http.get(`${API_BASE_URL}/api/v1/header/summary`, () =>
      HttpResponse.json({
        equity_eur: "0",
        pnl_day: "0",
        pnl_week: "0",
        pnl_month: "0",
        portfolio_dd_pct: "0",
        ks_level: 0,
        global_semaphore: "VERDE",
        mt_connected: true,
        open_positions: 0,
        alerts: 0,
        pending_decisions: 0,
        data_stale_seconds: null,
      })
    )
  );
}

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <RootLayout />,
        children: [
          { index: true, element: <div>pagina-resumen</div> },
          { path: "cuentas-ea", element: <div>pagina-cuentas</div> },
          { path: "bots", element: <div>pagina-bots</div> },
        ],
      },
      { path: "/login", element: <div>pagina-login</div> },
    ],
    { initialEntries: [path] }
  );
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

afterEach(() => {
  useAuthStore.setState({ accessToken: null, refreshToken: null });
  useAccountScopeStore.setState({ selectedAccountId: null });
});

describe("RootLayout: guard de cuenta", () => {
  it("sin sesion redirige a /login", async () => {
    renderAt("/bots");
    expect(await screen.findByText("pagina-login")).toBeInTheDocument();
  });

  it("con sesion pero sin cuenta elegida redirige cualquier pestaña a Cuentas", async () => {
    useAuthStore.setState({ accessToken: FAKE_ACCESS_TOKEN, refreshToken: "r" });
    mockBackend();
    renderAt("/bots");
    expect(await screen.findByText("pagina-cuentas")).toBeInTheDocument();
    expect(screen.queryByText("pagina-bots")).not.toBeInTheDocument();
  });

  it("con cuenta elegida deja pasar a la pestaña pedida", async () => {
    useAuthStore.setState({ accessToken: FAKE_ACCESS_TOKEN, refreshToken: "r" });
    useAccountScopeStore.setState({ selectedAccountId: 1 });
    mockBackend();
    renderAt("/bots");
    expect(await screen.findByText("pagina-bots")).toBeInTheDocument();
    // la seleccion sigue vigente una vez cargada la lista de cuentas
    await screen.findByRole("radio", { name: /BEPB/ });
    expect(screen.getByText("pagina-bots")).toBeInTheDocument();
    expect(useAccountScopeStore.getState().selectedAccountId).toBe(1);
  });
});
