import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { PipelinePanel } from "@/components/domain/PipelinePanel";
import { server } from "@/test/mocks/server";

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PipelinePanel />
    </QueryClientProvider>
  );
}

describe("PipelinePanel", () => {
  it("cuenta candidatos por fase (F4-F7, ADR 0012) e ignora PRODUCCION/CEMENTERIO", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/pipeline/board`, () =>
        HttpResponse.json([
          { id: 1, bot_id: 1, current_phase: "F4" },
          { id: 2, bot_id: 2, current_phase: "F4" },
          { id: 3, bot_id: 3, current_phase: "F7" },
          { id: 4, bot_id: 4, current_phase: "PRODUCCION" },
        ])
      ),
      http.get(`${API_BASE_URL}/api/v1/decisions`, () => HttpResponse.json([]))
    );
    renderPanel();

    expect(await screen.findByText("F4: 2")).toBeInTheDocument();
    expect(screen.getByText("F7: 1")).toBeInTheDocument();
    expect(screen.getByText("F5: 0")).toBeInTheDocument();
  });

  it("colorea las novedades por module (pipeline=GO, challenger=OVERSTAY, semaphore=NARANJA)", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/pipeline/board`, () => HttpResponse.json([])),
      http.get(`${API_BASE_URL}/api/v1/decisions`, () =>
        HttpResponse.json([
          { id: 1, module: "pipeline", title: "Sigma MR SPX — promoción disponible" },
          {
            id: 2,
            module: "challenger",
            title: "Helios Trend v2: challenger >6 meses sin superar al champion",
          },
          { id: 3, module: "semaphore", title: "Poseidón Trend GER40 en NARANJA sostenido" },
          { id: 4, module: "audit", title: "no deberia aparecer, module ajeno al panel" },
        ])
      )
    );
    renderPanel();

    expect(await screen.findByText("Sigma MR SPX — promoción disponible")).toBeInTheDocument();
    expect(screen.getByText("GO")).toBeInTheDocument();
    expect(screen.getByText("OVERSTAY")).toBeInTheDocument();
    expect(screen.getByText("NARANJA")).toBeInTheDocument();
    expect(screen.queryByText(/no deberia aparecer/)).not.toBeInTheDocument();
  });
});
