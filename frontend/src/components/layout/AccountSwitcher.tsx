import { useAccountScope } from "@/hooks/useAccountScope";
import { cn } from "@/lib/utils";
import uiStrings from "@/styles/ui_strings.es.json";

// ADR 0013: conmutador persistente de la cuenta activa (una opcion por cuenta
// con datos). Vive entre AppHeader y TabBar, fuera de `header .grid`.
export function AccountSwitcher() {
  const { accountId, accounts, selectAccount } = useAccountScope();
  return (
    <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-2">
      <span className="text-xs text-text-secondary">{uiStrings.accountScope.switcherLabel}</span>
      <div role="radiogroup" aria-label={uiStrings.accountScope.switcherLabel} className="flex gap-1">
        {accounts.map((account) => (
          <button
            key={account.id}
            type="button"
            role="radio"
            aria-checked={account.id === accountId}
            onClick={() => selectAccount(account.id)}
            className={cn(
              "rounded-md border px-3 py-1 text-xs font-medium transition-colors",
              account.id === accountId
                ? "border-accent-primary bg-accent-primary/10 text-text-primary"
                : "border-border-subtle text-text-secondary hover:text-text-primary"
            )}
          >
            {account.name}
            <span className="ml-1.5 text-text-muted">
              {account.is_demo ? uiStrings.accountScope.demo : uiStrings.accountScope.real}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
