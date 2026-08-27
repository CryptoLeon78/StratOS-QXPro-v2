import { useQuery } from "@tanstack/react-query";

import { getAccountEas, getAccounts, getAccountsDrift } from "@/api/endpoints/accounts";

export function useAccounts() {
  return useQuery({ queryKey: ["accounts"], queryFn: getAccounts });
}

export function useAccountEas(accountId: number) {
  return useQuery({ queryKey: ["account-eas", accountId], queryFn: () => getAccountEas(accountId) });
}

export function useAccountsDrift() {
  return useQuery({ queryKey: ["accounts-drift"], queryFn: getAccountsDrift });
}
