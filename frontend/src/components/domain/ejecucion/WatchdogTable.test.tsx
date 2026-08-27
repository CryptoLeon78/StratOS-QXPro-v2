import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { WatchdogTable } from "@/components/domain/ejecucion/WatchdogTable";
import { server } from "@/test/mocks/server";

function renderTable() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <WatchdogTable />
    </QueryClientProvider>
  );
}

describe("WatchdogTable", () => {
  it("cruza bot_id con /bots para mostrar el nombre real, no solo el id", async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/execution/watchdog`, () =>
        HttpResponse.json([
          {
            bot_id: 1,
            magic_number: 118231,
            state: "DEAD",
            observed_30d: 0,
            expected_month: 7,
            last_trade_at: null,
          },
        ])
      ),
      http.get(`${API_BASE_URL}/api/v1/bots`, () =>
        HttpResponse.json([{ id: 1, name: "Atlas Trend EURUSD" }])
      )
    );

    renderTable();

    expect(await screen.findByText("Atlas Trend EURUSD")).toBeInTheDocument();
    expect(screen.getByText("DEAD")).toBeInTheDocument();
  });
});
