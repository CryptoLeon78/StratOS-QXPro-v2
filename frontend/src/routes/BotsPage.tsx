import { useState } from "react";

import { BotDetail } from "@/components/domain/bots/BotDetail";
import { BotList } from "@/components/domain/bots/BotList";
import uiStrings from "@/styles/ui_strings.es.json";
import type { BotRow } from "@/api/endpoints/bots";

export default function BotsPage() {
  const [selected, setSelected] = useState<BotRow | null>(null);

  return (
    <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[280px_1fr]">
      <div className="lg:border-r lg:border-border-subtle lg:pr-4">
        <BotList selectedId={selected?.id ?? null} onSelect={setSelected} />
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
