import type { QueryClient } from "@tanstack/react-query";

import { useAccountScopeStore } from "@/stores/accountScopeStore";

// Al cambiar de cuenta se reinicia toda la cache salvo la lista de cuentas
// (no depende de la seleccion): `resetQueries` cancela las peticiones en
// vuelo -- una respuesta tardia de la cuenta anterior no puede reaparecer
// bajo la nueva -- y vuelve a pedir las queries activas con el nuevo
// `account_id` que `apiFetch` inyecta.
const ACCOUNT_INDEPENDENT_KEYS = new Set(["accounts", "recovery-status"]);

export function startAccountScopeSync(queryClient: QueryClient): () => void {
  return useAccountScopeStore.subscribe((state, previous) => {
    if (state.selectedAccountId === previous.selectedAccountId) {
      return;
    }
    void queryClient.resetQueries({
      predicate: (query) => !ACCOUNT_INDEPENDENT_KEYS.has(String(query.queryKey[0])),
    });
  });
}
