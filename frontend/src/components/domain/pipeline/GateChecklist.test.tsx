import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { GateChecklist } from "@/components/domain/pipeline/GateChecklist";
import { server } from "@/test/mocks/server";
import type { PipelineCandidate } from "@/api/endpoints/pipeline";

function renderChecklist(candidate: PipelineCandidate) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <GateChecklist candidate={candidate} />
    </QueryClientProvider>
  );
}

const baseCandidate: PipelineCandidate = {
  id: 1,
  bot_id: 1,
  account_id: 1,
  account_origin: "BROKER_DEMO",
  bot_origin: "INCUBATION",
  current_phase: "F5",
  entered_phase_at: "2026-01-01T00:00:00Z",
  incubation_days: 95,
  oos_trades: 51,
  profit_factor: 2.66,
  expectancy_r: 0.39,
  sharpe: 8.01,
  max_dd_pct: "1.3",
  wfe: 0.87,
  trades_per_week: 3.7,
  gates_passed: 7,
  gates_total: 7,
  provisional: false,
  verdict: "GO",
  verdict_reason: null,
  decision_eta_days: null,
  evaluated_at: "2026-01-01T00:00:00Z",
};

function mockThresholds() {
  server.use(
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

describe("GateChecklist", () => {
  it("marca los 7 criterios como cumplidos cuando todos superan el umbral", async () => {
    mockThresholds();
    renderChecklist(baseCandidate);

    expect(await screen.findByText(/2.66 \/ 1.5 ✓/)).toBeInTheDocument();
    expect(screen.getByText(/51 \/ 30 ✓/)).toBeInTheDocument();
    expect(screen.queryByText(/✗/)).not.toBeInTheDocument();
  });

  it("marca como fallido un criterio por debajo del umbral, y '—' cuando el valor es null", async () => {
    mockThresholds();
    renderChecklist({
      ...baseCandidate,
      profit_factor: 1.2,
      sharpe: null,
      oos_trades: 5,
    });

    expect(await screen.findByText(/1.2 \/ 1.5 ✗/)).toBeInTheDocument();
    expect(screen.getByText(/— \/ 1 ✗/)).toBeInTheDocument();
    expect(screen.getByText(/5 \/ 30 ✗/)).toBeInTheDocument();
  });
});
