import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { CorrelationMatrix } from "@/components/domain/portfolio/CorrelationMatrix";
import { server } from "@/test/mocks/server";

function renderMatrix() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CorrelationMatrix />
    </QueryClientProvider>
  );
}

describe("CorrelationMatrix", () => {
  it("muestra la media y los nombres de bot cruzados desde /bots", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/portfolio/correlations`, () =>
        HttpResponse.json([
          {
            bot_a_id: 1,
            bot_b_id: 2,
            correlation: 0.2,
            is_redundant_pair: false,
            ts: "2026-01-01T00:00:00Z",
          },
        ])
      ),
      http.get(`${API_BASE_URL}/api/v1/bots`, () =>
        HttpResponse.json([
          { id: 1, name: "Atlas Trend EURUSD" },
          { id: 2, name: "Helios Momentum DAX" },
        ])
      )
    );

    renderMatrix();

    expect(await screen.findByText("media 0.20")).toBeInTheDocument();
    expect(screen.getAllByText("Atlas Trend EURUSD").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Helios Momentum DAX").length).toBeGreaterThan(0);
  });

  it("estado vacio cuando no hay correlaciones calculadas todavia", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/portfolio/correlations`, () => HttpResponse.json([])),
      http.get(`${API_BASE_URL}/api/v1/bots`, () => HttpResponse.json([]))
    );

    renderMatrix();

    expect(await screen.findByText("Sin bots activos (F7/Producción) todavía.")).toBeInTheDocument();
  });
});
