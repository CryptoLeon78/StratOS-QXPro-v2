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
  account_id: 1,
  account_origin: "BROKER_DEMO",
  bot_origin: "INCUBATION",
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
  it("F1-F2 muestra el boton Promover", async () => {
    mockBotAndThresholds();
    renderCard({ ...baseCandidate, current_phase: "F2" });

    expect(await screen.findByRole("button", { name: "Promover a F3" })).toBeInTheDocument();
  });

  it("F3 bloquea la promocion y ofrece comprobar la admision demo", async () => {
    mockBotAndThresholds();
    server.use(
      http.post(`${API_BASE_URL}/api/v1/pipeline/1/demo-readiness`, () =>
        HttpResponse.json({
          candidate_id: 1,
          ready: false,
          requirements: [{ key: "demo_attachment_verified", satisfied: false }],
          next_action: "DEMO_ATTACHMENT_REQUIRED",
        })
      )
    );
    renderCard(baseCandidate);

    await screen.findByText("Vega Grid GBPUSD");
    expect(screen.queryByRole("button", { name: /Promover/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar adjunto demo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Comprobar admisión demo" })).toBeInTheDocument();
  });

  it("F5 muestra sólo lectura de observación demo y no ofrece promoción", async () => {
    mockBotAndThresholds();
    const observation = {
      candidate_id: 1, bot_id: 1, magic_number: 295, current_phase: "F5" as const,
      observation_started_at: "2026-09-10T00:00:00Z", tester_baseline: null,
      demo_trade_count: 0, demo_trade_first_open_at: null, demo_trade_last_close_at: null,
      valid_observation_days: 1, ea_state: { mode: "REAL", autotrading: true, ea_version: "v1.3", sizing_pct: "0.20", last_ingested_at: "2026-09-10T00:00:00Z" },
      latest_heartbeat_at: "2026-09-10T00:01:00Z", latest_equity: { ts: "2026-09-10T00:01:00Z", equity: "100.00", balance: "100.00", drawdown_pct: "0.000" },
      observation_status: "OBSERVED", missing_evidence: [],
    };
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><CandidateCard candidate={{ ...baseCandidate, current_phase: "F5" }} incubationObservation={observation} /></QueryClientProvider>);

    expect(await screen.findByText("Demo observada")).toBeInTheDocument();
    expect(screen.getByText("Trades demo: 0")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Promover/ })).not.toBeInTheDocument();
  });
});
