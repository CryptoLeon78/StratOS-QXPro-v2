import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { DriftPanel } from "@/components/domain/cuentas-ea/DriftPanel";
import { server } from "@/test/mocks/server";

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DriftPanel />
    </QueryClientProvider>
  );
}

describe("DriftPanel", () => {
  it("solo muestra las filas con drift=true, ignora las que coinciden", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/accounts/drift`, () =>
        HttpResponse.json([
          { bot_id: 1, account_id: 1, magic_number: 118231, expected_mode: "REAL", reported_mode: "REAL", drift: false },
          { bot_id: 2, account_id: 1, magic_number: 118247, expected_mode: "PAPER", reported_mode: "REAL", drift: true },
        ])
      )
    );

    renderPanel();

    expect(await screen.findByText(/Bot #2 \(magic 118247\): esperado PAPER, reportado REAL/)).toBeInTheDocument();
    expect(screen.queryByText(/Bot #1/)).not.toBeInTheDocument();
    expect(screen.queryByText("Sin deriva detectada")).not.toBeInTheDocument();
  });

  it("estado vacio cuando ningun EA tiene deriva", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/accounts/drift`, () =>
        HttpResponse.json([
          { bot_id: 1, account_id: 1, magic_number: 118231, expected_mode: "REAL", reported_mode: "REAL", drift: false },
        ])
      )
    );

    renderPanel();

    expect(
      await screen.findByText("Sin deriva detectada — todos los EAs reportan el modo esperado.")
    ).toBeInTheDocument();
  });
});
