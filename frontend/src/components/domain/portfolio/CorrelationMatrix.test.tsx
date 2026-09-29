import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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
  it("lista los bots instalados excluidos con su motivo y marca la baja confianza", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/portfolio/correlations/latest`, ({ request }) => {
        if (new URL(request.url).searchParams.get("source") !== "MT5_REAL") return HttpResponse.json(null);
        return HttpResponse.json({
          id: 1, source: "MT5_REAL", status: "COMPLETED", reason: null,
          created_at: "2026-09-29T00:00:00Z", window_start: null, window_end: null, window_days: 1240,
          algorithm_version: "daily-net-pnl-v2", account_scope: { account_id: 2 },
          input_sha256: "a".repeat(64),
          pairs: [{ bot_a_id: 1, bot_b_id: 2, correlation: 0.2, is_redundant_pair: false, snapshot_id: 1, source: "MT5_REAL", created_at: "2026-09-29T00:00:00Z", n_obs: 12, low_confidence: true }],
        });
      }),
      http.get(`${API_BASE_URL}/api/v1/portfolio/correlations/coverage`, ({ request }) => {
        if (new URL(request.url).searchParams.get("source") !== "MT5_REAL") return HttpResponse.json([]);
        return HttpResponse.json([
          { bot_id: 1, name: "Atlas", included: true, days: 12, trades: 12, reason: null },
          { bot_id: 2, name: "Helios", included: true, days: 12, trades: 12, reason: null },
          { bot_id: 3, name: "Zeta Corto", included: false, days: 3, trades: 3, reason: "HISTORIA_INSUFICIENTE" },
        ]);
      }),
      http.get(`${API_BASE_URL}/api/v1/bots`, () => HttpResponse.json([{ id: 1, name: "Atlas" }, { id: 2, name: "Helios" }])),
      http.get(`${API_BASE_URL}/api/v1/accounts`, () => HttpResponse.json([]))
    );

    renderMatrix();

    expect(await screen.findByText("Zeta Corto")).toBeInTheDocument();
    expect(screen.getByText(/Historia insuficiente/)).toBeInTheDocument();
    expect(screen.getByText(/3 días · 3 operaciones/)).toBeInTheDocument();
    expect(screen.getByText(/Baja confianza/)).toBeInTheDocument();
  });

  it("muestra la media y los nombres de bot cruzados desde /bots", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/portfolio/correlations/latest`, ({ request }) => {
        if (new URL(request.url).searchParams.get("source") !== "MT5_REAL") return HttpResponse.json(null);
        return HttpResponse.json({
          id: 1, source: "MT5_REAL", status: "COMPLETED", reason: null,
          created_at: "2026-01-01T00:00:00Z", window_start: "2025-01-01T00:00:00Z",
          window_end: "2026-01-01T00:00:00Z", window_days: 365,
          algorithm_version: "daily-net-pnl-v2", account_scope: { account_ids: [1] },
          input_sha256: "a".repeat(64),
          pairs: [{ bot_a_id: 1, bot_b_id: 2, correlation: 0.2, is_redundant_pair: false, snapshot_id: 1, source: "MT5_REAL", created_at: "2026-01-01T00:00:00Z" }],
        });
      }),
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
      http.get(`${API_BASE_URL}/api/v1/portfolio/correlations/latest`, () => HttpResponse.json(null)),
      http.get(`${API_BASE_URL}/api/v1/bots`, () => HttpResponse.json([]))
    );

    renderMatrix();

    await waitFor(() => {
      expect(screen.getAllByText("Aún no existe un snapshot sellado para esta fuente.")).toHaveLength(2);
    });
  });
});
