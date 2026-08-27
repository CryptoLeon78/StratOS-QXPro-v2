// diseño derivado, sin captura de referencia (PARTE 7.2)
import { AccountCard } from "@/components/domain/cuentas-ea/AccountCard";
import { DriftPanel } from "@/components/domain/cuentas-ea/DriftPanel";
import { TcaPendingCard } from "@/components/domain/TcaPendingCard";
import { useAccounts } from "@/hooks/queries/useAccounts";
import { useBots } from "@/hooks/queries/useBots";
import uiStrings from "@/styles/ui_strings.es.json";

export default function CuentasEaPage() {
  const { data: accounts, isLoading } = useAccounts();
  const { data: bots } = useBots();

  return (
    <div className="space-y-4 p-4">
      {!isLoading && (accounts ?? []).length === 0 && (
        <p className="text-sm text-text-secondary">{uiStrings.cuentasEa.emptyAccounts}</p>
      )}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(accounts ?? []).map((account) => (
          <AccountCard key={account.id} account={account} bots={bots ?? []} />
        ))}
      </div>
      <DriftPanel />
      <TcaPendingCard />
    </div>
  );
}
