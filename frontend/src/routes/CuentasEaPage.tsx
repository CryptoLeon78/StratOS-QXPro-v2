// ADR 0013. Primera pestaña: selector de cuenta (una opcion por cuenta con datos) y,
// debajo, el detalle de la cuenta elegida (diseño derivado, sin captura, PARTE 7.2).
import { Link, useLocation } from "react-router-dom";

import { QueryError } from "@/components/domain/QueryError";
import { AccountCard } from "@/components/domain/cuentas-ea/AccountCard";
import { AccountSelectorCard } from "@/components/domain/cuentas-ea/AccountSelectorCard";
import { DriftPanel } from "@/components/domain/cuentas-ea/DriftPanel";
import { TcaPendingCard } from "@/components/domain/TcaPendingCard";
import { useBots } from "@/hooks/queries/useBots";
import { useAccountScope } from "@/hooks/useAccountScope";
import uiStrings from "@/styles/ui_strings.es.json";

export default function CuentasEaPage() {
  const { accountId, account, accounts, isLoading, isError, refetch, selectAccount } = useAccountScope();
  const { data: bots } = useBots();
  const { state } = useLocation();
  const needAccount = (state as { needAccount?: boolean } | null)?.needAccount === true;

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-base font-semibold text-text-primary">{uiStrings.accountScope.pickTitle}</h2>
        <p className="text-xs text-text-secondary">
          {needAccount && accountId === null
            ? uiStrings.accountScope.needAccount
            : uiStrings.accountScope.pickHint}
        </p>
      </div>
      {isError && <QueryError onRetry={() => void refetch()} />}
      {!isLoading && !isError && accounts.length === 0 && (
        <p className="text-sm text-text-secondary">{uiStrings.cuentasEa.emptyAccounts}</p>
      )}
      <div role="radiogroup" aria-label={uiStrings.accountScope.pickTitle} className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {accounts.map((candidate) => (
          <AccountSelectorCard
            key={candidate.id}
            account={candidate}
            selected={candidate.id === accountId}
            onSelect={() => selectAccount(candidate.id)}
          />
        ))}
      </div>
      {account && (
        <>
          <Link to="/" className="inline-block text-sm text-accent-primary hover:underline">
            {uiStrings.accountScope.goToSummary}
          </Link>
          <AccountCard account={account} bots={bots ?? []} />
          <DriftPanel />
          <TcaPendingCard />
        </>
      )}
    </div>
  );
}
