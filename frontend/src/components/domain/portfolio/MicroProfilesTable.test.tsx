import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { MicroProfilesTable } from "@/components/domain/portfolio/MicroProfilesTable";
import { server } from "@/test/mocks/server";

function renderTable() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MicroProfilesTable />
    </QueryClientProvider>
  );
}

describe("MicroProfilesTable", () => {
  it("fusiona GRID y SCALPING en una unica fila 'Grid / Scalping' (ADR)", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/portfolio/profiles`, () =>
        HttpResponse.json([
          { key: "TREND", target_pct: 30, real_pct: 27.2, delta_pct: -2.8, bot_count: 12 },
          { key: "GRID", target_pct: 5, real_pct: 4.0, delta_pct: -1.0, bot_count: 3 },
          { key: "SCALPING", target_pct: 5, real_pct: 5.8, delta_pct: 0.8, bot_count: 3 },
        ])
      )
    );

    renderTable();

    expect(await screen.findByText("Grid / Scalping")).toBeInTheDocument();
    expect(screen.getByText("10%")).toBeInTheDocument(); // target sumado
    expect(screen.getByText("9.8%")).toBeInTheDocument(); // real sumado
    expect(screen.getByText("6")).toBeInTheDocument(); // bots sumados
    expect(screen.queryByText(/^GRID$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^SCALPING$/)).not.toBeInTheDocument();
  });

  it("no revienta si no hay ni GRID ni SCALPING en la respuesta", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/portfolio/profiles`, () =>
        HttpResponse.json([
          { key: "TREND", target_pct: 30, real_pct: 27.2, delta_pct: -2.8, bot_count: 12 },
        ])
      )
    );

    renderTable();

    expect(await screen.findByText("Trend Following")).toBeInTheDocument();
    expect(screen.queryByText("Grid / Scalping")).not.toBeInTheDocument();
  });
});
