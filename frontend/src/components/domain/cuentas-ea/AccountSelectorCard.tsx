import type { AccountRow } from "@/api/endpoints/accounts";
import { Badge } from "@/components/ui/badge";
import { formatAmount } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import uiStrings from "@/styles/ui_strings.es.json";

// ADR 0013: opcion del selector de cuenta (primera pestaña). Rol Real/Demo
// derivado de `Account.is_demo`, nombre de `Account.name`.
export function AccountSelectorCard({
  account,
  selected,
  onSelect,
}: {
  account: AccountRow;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "rounded-lg border p-4 text-left transition-colors",
        selected
          ? "border-accent-primary bg-accent-primary/10"
          : "border-border-subtle hover:border-text-secondary"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-base font-semibold text-text-primary">{account.name}</span>
        <Badge variant={account.is_demo ? "outline" : "default"}>
          {account.is_demo ? uiStrings.accountScope.demo : uiStrings.accountScope.real}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-text-secondary">
        {account.broker} · {account.login}
      </p>
      <dl className="mt-3 flex gap-6 text-xs">
        <div>
          <dt className="text-text-secondary">{uiStrings.accountScope.equity}</dt>
          <dd className="font-semibold text-text-primary">
            {account.equity === null ? "—" : formatAmount(account.equity)}
          </dd>
        </div>
        <div>
          <dt className="text-text-secondary">&nbsp;</dt>
          <dd className="font-semibold text-text-primary">
            {interpolate(uiStrings.accountScope.botCount, { n: account.bot_count })}
          </dd>
        </div>
      </dl>
      {selected && <p className="mt-2 text-xs text-accent-primary">{uiStrings.accountScope.selected}</p>}
    </button>
  );
}
