import { useEffect } from "react";

import type { AccountRow } from "@/api/endpoints/accounts";
import { useAccounts } from "@/hooks/queries/useAccounts";
import { useAccountScopeStore } from "@/stores/accountScopeStore";

// Una cuenta es elegible si esta activa y tiene datos (bots o equity): la
// fila INCUBADORA vacia (id 3 en el operacional) no debe ofrecerse.
export function isSelectableAccount(account: AccountRow): boolean {
  return account.is_active && (account.bot_count > 0 || account.equity !== null);
}

export function useSelectableAccounts() {
  const query = useAccounts();
  return { ...query, accounts: (query.data ?? []).filter(isSelectableAccount) };
}

export function useAccountScope() {
  const accountId = useAccountScopeStore((state) => state.selectedAccountId);
  const selectAccount = useAccountScopeStore((state) => state.selectAccount);
  const clearAccount = useAccountScopeStore((state) => state.clearAccount);
  const { accounts, data, isLoading, isError, refetch } = useSelectableAccounts();
  const account = accounts.find((candidate) => candidate.id === accountId);

  // Una seleccion persistida que ya no existe (cuenta retirada o vaciada) se
  // descarta -- solo cuando la lista ya cargo, nunca por un fallo de red.
  useEffect(() => {
    if (accountId !== null && data !== undefined && account === undefined) {
      clearAccount();
    }
  }, [accountId, data, account, clearAccount]);

  return { accountId, account, accounts, isLoading, isError, refetch, selectAccount };
}
