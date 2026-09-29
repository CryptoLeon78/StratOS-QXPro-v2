import { useSearchParams } from "react-router-dom";

import { BotDetail } from "@/components/domain/bots/BotDetail";
import { BotList } from "@/components/domain/bots/BotList";
import { useBots } from "@/hooks/queries/useBots";
import { sortBotsForList } from "@/lib/botOrder";
import uiStrings from "@/styles/ui_strings.es.json";

// El bot elegido vive en la URL (`?bot=ID`): enlace directo y sobrevive a
// recargas. Sin `?bot` (o con un id ajeno a la cuenta activa) se abre el
// primero de la lista, en el mismo orden que ve el operador.
export default function BotsPage() {
  const { data: bots } = useBots();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedId = Number(searchParams.get("bot"));
  const ordered = sortBotsForList(bots ?? []);
  const selected = ordered.find((bot) => bot.id === requestedId) ?? ordered.at(0) ?? null;

  return (
    <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[280px_1fr]">
      <div className="lg:border-r lg:border-border-subtle lg:pr-4">
        <BotList
          selectedId={selected?.id ?? null}
          onSelect={(bot) => setSearchParams({ bot: String(bot.id) }, { replace: true })}
        />
      </div>
      <div>
        {selected ? (
          <BotDetail bot={selected} />
        ) : (
          <p className="text-sm text-text-secondary">{uiStrings.bots.emptySelection}</p>
        )}
      </div>
    </div>
  );
}
