import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { MonthlyEvolutionTable } from "@/components/domain/escalado/MonthlyEvolutionTable";
import { server } from "@/test/mocks/server";

function renderTable() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MonthlyEvolutionTable />
    </QueryClientProvider>
  );
}

describe("MonthlyEvolutionTable", () => {
  it("muestra Sharpe cuando el JSON libre lo trae, y '—' cuando no (bajada automatica sin firma)", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/scaling/monthly`, () =>
        HttpResponse.json([
          {
            id: 1,
            ts: "2026-02-01T00:00:00Z",
            phase: 3,
            equity_at: "80000",
            metrics: { sharpe: 1.4, dd_pct: "4.1" },
            ready_to_advance: true,
            signed_by: "ivan",
          },
          {
            id: 2,
            ts: "2026-03-01T00:00:00Z",
            phase: 2,
            equity_at: "20000",
            metrics: {},
            ready_to_advance: false,
            signed_by: null,
          },
        ])
      )
    );

    renderTable();

    expect(await screen.findByText("1.40")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("estado vacio sin historial", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/scaling/monthly`, () => HttpResponse.json([]))
    );

    renderTable();

    expect(
      await screen.findByText("Sin historial de fases UMS todavía.")
    ).toBeInTheDocument();
  });
});
