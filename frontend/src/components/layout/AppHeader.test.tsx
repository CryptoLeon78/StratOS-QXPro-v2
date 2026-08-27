import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { AppHeader } from "@/components/layout/AppHeader";
import { API_BASE_URL } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { server } from "@/test/mocks/server";

// header claims={sub:"1",email:"dev@stratos.local",role:"operator",exp:9999999999}
const FAKE_ACCESS_TOKEN =
  "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJkZXZAc3RyYXRvcy5sb2NhbCIsInJvbGUiOiJvcGVyYXRvciIsImV4cCI6OTk5OTk5OTk5OX0.fake";

function renderAppHeader() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AppHeader />
    </QueryClientProvider>
  );
}

function mockHeaderSummary(overrides: Record<string, unknown> = {}) {
  server.use(
    http.get(`${API_BASE_URL}/api/v1/header/summary`, () =>
      HttpResponse.json({
        equity_eur: "179642.70",
        pnl_day: "37.36",
        pnl_week: "2444.14",
        pnl_month: "10525.70",
        portfolio_dd_pct: "0.4",
        ks_level: 0,
        global_semaphore: "NARANJA",
        mt_connected: true,
        open_positions: 3,
        alerts: 2,
        pending_decisions: 2,
        data_stale_seconds: null,
        ...overrides,
      })
    )
  );
}

beforeEach(() => {
  useAuthStore.getState().setSession(FAKE_ACCESS_TOKEN, "refresh");
});

describe("AppHeader", () => {
  it("muestra las 6 StatCard con los datos reales del header/summary", async () => {
    mockHeaderSummary();
    renderAppHeader();

    expect(await screen.findByText("179.642,70")).toBeInTheDocument();
    expect(screen.getByText("+37,36")).toBeInTheDocument();
    expect(screen.getByText("Sem: 2.444,14 · Mes: 10.525,70")).toBeInTheDocument();
    expect(screen.getByText("0,4%")).toBeInTheDocument();
    expect(screen.getByText("KS L0: Sin activación")).toBeInTheDocument();
    expect(screen.getByText("Naranja")).toBeInTheDocument();
    expect(screen.getByText("Conectado")).toBeInTheDocument();
    expect(screen.getByText("3 pos. abiertas")).toBeInTheDocument();
    expect(screen.getByText("2 decisiones")).toBeInTheDocument();
    expect(screen.getByText("Ingeniero")).toBeInTheDocument();
  });

  it("un P&L negativo se muestra en rojo, no en verde", async () => {
    mockHeaderSummary({ pnl_day: "-12.50" });
    renderAppHeader();

    const value = await screen.findByText("-12,50");
    expect(value.className).toContain("text-pnl-negative");
  });

  it("con ks_level>0 muestra el nivel activo en vez de 'Sin activacion'", async () => {
    mockHeaderSummary({ ks_level: 2 });
    renderAppHeader();

    expect(await screen.findByText("KS L2: nivel activo")).toBeInTheDocument();
  });

  it("con data_stale_seconds muestra el badge DATOS STALE", async () => {
    mockHeaderSummary({ data_stale_seconds: 125 });
    renderAppHeader();

    expect(await screen.findByText("DATOS STALE (hace 2 min)")).toBeInTheDocument();
  });

  it("sin data_stale_seconds no muestra el badge DATOS STALE", async () => {
    mockHeaderSummary({ data_stale_seconds: null });
    renderAppHeader();

    await waitFor(() => expect(screen.getByText("179.642,70")).toBeInTheDocument());
    expect(screen.queryByText(/DATOS STALE/)).not.toBeInTheDocument();
  });
});
