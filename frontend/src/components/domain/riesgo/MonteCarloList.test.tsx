import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { MonteCarloList } from "@/components/domain/riesgo/MonteCarloList";
import { server } from "@/test/mocks/server";

function renderList() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MonteCarloList />
    </QueryClientProvider>
  );
}

describe("MonteCarloList", () => {
  it("marca 'fuera del perfil esperado' cuando dd_p95 supera el contrato firmado", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/bots`, () =>
        HttpResponse.json([
          { id: 1, name: "Bot Dentro", magic_number: 111, pipeline_phase: "F7" },
          { id: 2, name: "Bot Fuera", magic_number: 222, pipeline_phase: "PRODUCCION" },
          { id: 3, name: "Bot Paper", magic_number: 333, pipeline_phase: "F3" },
        ])
      ),
      http.get(`${API_BASE_URL}/api/v1/risk/montecarlo`, ({ request }) => {
        const botId = new URL(request.url).searchParams.get("bot_id");
        if (botId === "1") {
          return HttpResponse.json({
            bot_id: 1,
            ts: "2026-01-01T00:00:00Z",
            n_simulations: 300,
            dd_p50: "2.0",
            dd_p75: "2.8",
            dd_p95: "3.5",
            dd_contract_pct: "3.9",
            seed: 1,
          });
        }
        return HttpResponse.json({
          bot_id: 2,
          ts: "2026-01-01T00:00:00Z",
          n_simulations: 300,
          dd_p50: "2.0",
          dd_p75: "2.8",
          dd_p95: "4.5",
          dd_contract_pct: "3.9",
          seed: 2,
        });
      })
    );

    renderList();

    expect(await screen.findByText("Dentro del perfil esperado — no intervenir")).toBeInTheDocument();
    expect(await screen.findByText("Fuera del perfil esperado — revisar")).toBeInTheDocument();
    expect(screen.queryByText("Bot Paper")).not.toBeInTheDocument();
  });
});
