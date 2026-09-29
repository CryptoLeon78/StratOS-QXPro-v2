import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it } from "vitest";

import { startAccountScopeSync } from "@/lib/accountScopeSync";
import { useAccountScopeStore } from "@/stores/accountScopeStore";

afterEach(() => {
  useAccountScopeStore.setState({ selectedAccountId: null });
});

describe("startAccountScopeSync", () => {
  it("al cambiar de cuenta descarta la cache salvo la lista de cuentas", async () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(["bots"], [{ id: 1 }]);
    queryClient.setQueryData(["accounts"], [{ id: 1 }]);
    const stop = startAccountScopeSync(queryClient);

    useAccountScopeStore.getState().selectAccount(3);
    await Promise.resolve();

    expect(queryClient.getQueryData(["bots"])).toBeUndefined();
    expect(queryClient.getQueryData(["accounts"])).toEqual([{ id: 1 }]);
    stop();
  });

  it("no toca la cache si la cuenta no cambia", async () => {
    const queryClient = new QueryClient();
    useAccountScopeStore.setState({ selectedAccountId: 3 });
    queryClient.setQueryData(["bots"], [{ id: 1 }]);
    const stop = startAccountScopeSync(queryClient);

    useAccountScopeStore.getState().selectAccount(3);
    await Promise.resolve();

    expect(queryClient.getQueryData(["bots"])).toEqual([{ id: 1 }]);
    stop();
  });
});
