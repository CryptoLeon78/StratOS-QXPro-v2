import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { HealthCard } from "@/components/domain/salud/HealthCard";
import { server } from "@/test/mocks/server";
import type { HealthRow } from "@/api/endpoints/health";

function renderCard(bot: HealthRow) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <HealthCard bot={bot} />
    </QueryClientProvider>
  );
}

const baseBot: HealthRow = {
  bot_id: 1,
  magic_number: 118318,
  name: "Vega Grid GBPUSD",
  profile: "GRID",
  pipeline_phase: "F7",
  semaphore_state: "NARANJA",
  days_in_state: 6,
  pf_rolling: 1.1,
  pf_baseline: 1.8,
  exp_rolling: 0.1,
  exp_baseline: 0.2,
  loss_streak: 3,
  dd_bot_pct: "1.30",
  dd_contract_pct: "3.90",
  page_hinkley_triggered: false,
};

function mockInstructions() {
  server.use(
    http.get(`${API_BASE_URL}/api/v1/config/semaphore-instructions`, () =>
      HttpResponse.json({
        verde: "Mantener. No tocar nada.",
        amarillo: "Reducir sizing al 50%.",
        naranja_template: "En el EA magic {magic}: desactivar apertura de nuevas posiciones.",
      })
    )
  );
}

describe("HealthCard", () => {
  it("interpola el magic number real en la instruccion NARANJA", async () => {
    mockInstructions();
    renderCard(baseBot);

    expect(
      await screen.findByText("En el EA magic 118318: desactivar apertura de nuevas posiciones.")
    ).toBeInTheDocument();
  });

  it("muestra la instruccion VERDE sin interpolar nada", async () => {
    mockInstructions();
    renderCard({ ...baseBot, semaphore_state: "VERDE" });

    expect(await screen.findByText("Mantener. No tocar nada.")).toBeInTheDocument();
  });

  it("PH se muestra como Si/No, nunca como numero inventado", async () => {
    mockInstructions();
    renderCard({ ...baseBot, page_hinkley_triggered: true });

    expect(await screen.findByText("PH Sí")).toBeInTheDocument();
  });
});
