import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it } from "vitest";

import { API_BASE_URL } from "@/api/client";
import { AccountSwitcher } from "@/components/layout/AccountSwitcher";
import { useAccountScopeStore } from "@/stores/accountScopeStore";
import { server } from "@/test/mocks/server";

const account = (overrides: Record<string, unknown>) => ({
  id: 1,
  name: "BEPB",
  broker: "Darwinex",
  login: "1",
  server: "s",
  currency: "EUR",
  is_demo: false,
  data_origin: "BROKER_REAL",
  is_active: true,
  equity: "1000",
  balance: "1000",
  free_margin: null,
  margin_level: null,
  equity_ts: null,
  bot_count: 3,
  ...overrides,
});

function mockAccounts() {
  server.use(
    http.get(`${API_BASE_URL}/api/v1/accounts`, () =>
      HttpResponse.json([
        account({ id: 1, name: "BEPB" }),
        account({ id: 2, name: "JJTI", login: "2" }),
        account({ id: 4, name: "INCUBADORA_DEMO", is_demo: true, data_origin: "BROKER_DEMO", bot_count: 2, equity: null }),
        account({ id: 3, name: "INCUBADORA", is_demo: true, data_origin: "BROKER_DEMO", bot_count: 0, equity: null }),
      ])
    )
  );
}

function renderSwitcher() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AccountSwitcher />
    </QueryClientProvider>
  );
}

afterEach(() => {
  useAccountScopeStore.setState({ selectedAccountId: null });
});

describe("AccountSwitcher", () => {
  it("ofrece solo las cuentas con datos (oculta la cuenta vacia)", async () => {
    mockAccounts();
    renderSwitcher();

    expect(await screen.findByRole("radio", { name: /BEPB/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /JJTI/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /INCUBADORA_DEMO/ })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: /^INCUBADORA\b(?!_)/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(3);
  });

  it("elegir una cuenta la marca y la guarda en el store", async () => {
    mockAccounts();
    renderSwitcher();

    await userEvent.click(await screen.findByRole("radio", { name: /JJTI/ }));

    expect(useAccountScopeStore.getState().selectedAccountId).toBe(2);
    expect(screen.getByRole("radio", { name: /JJTI/ })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: /BEPB/ })).toHaveAttribute("aria-checked", "false");
  });

  it("descarta una seleccion persistida que ya no existe", async () => {
    mockAccounts();
    useAccountScopeStore.setState({ selectedAccountId: 99 });
    renderSwitcher();

    await screen.findByRole("radio", { name: /BEPB/ });
    await waitFor(() => expect(useAccountScopeStore.getState().selectedAccountId).toBeNull());
  });
});
