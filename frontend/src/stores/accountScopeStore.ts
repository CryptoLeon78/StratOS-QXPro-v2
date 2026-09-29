import { create } from "zustand";
import { persist } from "zustand/middleware";

// ADR 0013: la cuenta elegida gobierna TODA la UI. Solo se persiste el id;
// nombre/rol/origen se derivan siempre de GET /accounts (Account.name,
// Account.data_origin), nunca de una lista escrita en el frontend.
// `api/client.ts` anade `account_id` a cada peticion /api/v1/* y
// `lib/accountScopeSync.ts` descarta la cache al cambiar de cuenta.
interface AccountScopeState {
  selectedAccountId: number | null;
  selectAccount: (accountId: number) => void;
  clearAccount: () => void;
}

export const useAccountScopeStore = create<AccountScopeState>()(
  persist(
    (set) => ({
      selectedAccountId: null,
      selectAccount: (accountId) => set({ selectedAccountId: accountId }),
      clearAccount: () => set({ selectedAccountId: null }),
    }),
    { name: "stratos-account-scope" }
  )
);
