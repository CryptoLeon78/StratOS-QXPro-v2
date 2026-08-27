import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { CandidateCard } from "@/components/domain/pipeline/CandidateCard";
import { server } from "@/test/mocks/server";
import type { PipelineCandidate } from "@/api/endpoints/pipeline";

function renderCard(candidate: PipelineCandidate) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CandidateCard candidate={candidate} />
    </QueryClientProvider>
  );
}

const baseCandidate: PipelineCandidate = {
  id: 1,
  bot_id: 1,
  current_phase: "F3",
  entered_phase_at: "2026-01-01T00:00:00Z",
  incubation_days: 38,
  oos_trades: 12,
  profit_factor: 1.2,
  expectancy_r: 0.05,
  sharpe: 0.6,
  max_dd_pct: "6.2",
  wfe: 0.41,
  trades_per_week: 1.1,
  gates_passed: 0,
  gates_total: 7,
  provisional: true,
  verdict: null,
  verdict_reason: null,
  decision_eta_days: null,
  evaluated_at: null,
};

function mockBotAndThresholds() {
  server.use(
    http.get(`${API_BASE_URL}/api/v1/bots/1`, () =>
      HttpResponse.json({ id: 1, name: "Vega Grid GBPUSD" })
    ),
    http.get(`${API_BASE_URL}/api/v1/config/pipeline-gate`, () =>
      HttpResponse.json({
        min_trades: 30,
        min_days: 60,
        pf: 1.5,
        exp: 0.15,
        sharpe: 1.0,
        maxdd: 20.0,
        min_freq_week: 2.0,
        kill_pf: 1.1,
        marginal_band: 0.1,
      })
    )
  );
}

describe("CandidateCard", () => {
  it("F1-F3 muestra el boton Promover", async () => {
    mockBotAndThresholds();
    renderCard(baseCandidate);

    expect(await screen.findByRole("button", { name: "Promover a F4" })).toBeInTheDocument();
  });

  it("F4+ NO muestra boton Promover (P6.3: solo gate automatico)", async () => {
    mockBotAndThresholds();
    renderCard({ ...baseCandidate, current_phase: "F5", bot_id: 1 });

    await screen.findByText("Vega Grid GBPUSD");
    expect(screen.queryByRole("button", { name: /Promover/ })).not.toBeInTheDocument();
  });
});
