import { Badge } from "@/components/ui/badge";
import { useAccountScope } from "@/hooks/useAccountScope";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

// ADR 0013: el Resumen declara de que cuenta son las cifras que muestra.
export function AccountBanner() {
  const { account } = useAccountScope();
  if (!account) {
    return null;
  }
  const kind = account.is_demo ? uiStrings.accountScope.demo : uiStrings.accountScope.real;
  return (
    <div className="flex items-center gap-2" data-testid="account-banner">
      <Badge variant={account.is_demo ? "outline" : "default"}>{kind}</Badge>
      <span className="text-sm text-text-secondary">
        {interpolate(uiStrings.accountScope.summaryBanner, {
          name: account.name,
          kind,
          login: account.login,
        })}
      </span>
    </div>
  );
}
