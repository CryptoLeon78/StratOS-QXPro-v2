import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { EquityCard } from "@/components/domain/EquityCard";
import { server } from "@/test/mocks/server";
import uiStrings from "@/styles/ui_strings.es.json";

function renderCard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <EquityCard />
    </QueryClientProvider>
  );
}

function mockHeader(dataStaleSeconds: number | null) {
  server.use(
    http.get(`${API_BASE_URL}/api/v1/header/summary`, () =>
      HttpResponse.json({
        equity_eur: "0",
        pnl_day: "0",
        pnl_week: "0",
        pnl_month: "0",
        portfolio_dd_pct: "0",
        ks_level: 0,
        global_semaphore: "VERDE",
        mt_connected: false,
        open_positions: 0,
        alerts: 0,
        pending_decisions: 0,
        data_stale_seconds: dataStaleSeconds,
      })
    ),
    http.get(`${API_BASE_URL}/api/v1/summary/equity-curve`, () =>
      HttpResponse.json([{ date: "2026-08-26", equity: "179642.70" }])
    )
  );
}

describe("EquityCard", () => {
  it("con data_stale_seconds no nulo, atenua la cifra y muestra el aviso", async () => {
    mockHeader(600);
    renderCard();

    expect(await screen.findByText(uiStrings.equityCard.staleNotice)).toBeInTheDocument();
  });

  it("sin data_stale_seconds, no muestra el aviso", async () => {
    mockHeader(null);
    renderCard();

    expect(await screen.findByText("179.642,70")).toBeInTheDocument();
    expect(screen.queryByText(uiStrings.equityCard.staleNotice)).not.toBeInTheDocument();
  });
});
