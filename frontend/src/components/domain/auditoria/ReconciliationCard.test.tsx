import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { ReconciliationCard } from "@/components/domain/auditoria/ReconciliationCard";
import { server } from "@/test/mocks/server";

function renderCard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReconciliationCard />
    </QueryClientProvider>
  );
}

describe("ReconciliationCard", () => {
  it("marca DESCUADRE cuando breached=true, OK en caso contrario", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/audit/status`, () =>
        HttpResponse.json([
          {
            account_id: 1,
            initial_balance: "30000.00",
            flows: "147616.18",
            final_balance: "177616.18",
            expected: "177616.18",
            discrepancy_pct: "0.00",
            breached: false,
          },
          {
            account_id: 2,
            initial_balance: "10000.00",
            flows: "500.00",
            final_balance: "10600.00",
            expected: "10500.00",
            discrepancy_pct: "0.95",
            breached: true,
          },
        ])
      )
    );

    renderCard();

    expect(await screen.findByText("OK")).toBeInTheDocument();
    expect(screen.getByText("DESCUADRE")).toBeInTheDocument();
  });

  it("descuadre null se muestra como '—', nunca como 0%", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/audit/status`, () =>
        HttpResponse.json([
          {
            account_id: 1,
            initial_balance: "30000.00",
            flows: "0.00",
            final_balance: "30000.00",
            expected: "30000.00",
            discrepancy_pct: null,
            breached: false,
          },
        ])
      )
    );

    renderCard();

    expect(await screen.findByText("—")).toBeInTheDocument();
  });
});
