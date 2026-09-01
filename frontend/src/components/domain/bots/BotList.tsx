import { useState } from "react";

import { SemaphoreBadge } from "@/components/domain/SemaphoreBadge";
import { Input } from "@/components/ui/input";
import { useBots } from "@/hooks/queries/useBots";
import uiStrings from "@/styles/ui_strings.es.json";
import type { BotRow } from "@/api/endpoints/bots";

// PARTE 7.4: lista maestro, agrupada por `pipeline_phase` (la captura solo
// muestra "PRODUCCION (28)" porque en el dataset de referencia es la unica
// fase con bots -- aqui se agrupa dinamicamente por lo que devuelva /bots).
export function BotList({
  selectedId,
  onSelect,
}: {
  selectedId: number | null;
  onSelect: (bot: BotRow) => void;
}) {
  const { data } = useBots();
  const [query, setQuery] = useState("");

  const filtered = (data ?? []).filter((bot) =>
    bot.name.toLowerCase().includes(query.toLowerCase())
  );
  const groups = new Map<string, BotRow[]>();
  for (const bot of filtered) {
    const group = groups.get(bot.pipeline_phase) ?? [];
    group.push(bot);
    groups.set(bot.pipeline_phase, group);
  }

  return (
    <div className="flex h-full flex-col gap-2">
      <Input
        placeholder={uiStrings.bots.searchPlaceholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {filtered.length === 0 && (
        <p className="p-2 text-xs text-text-secondary">{uiStrings.bots.emptySearch}</p>
      )}
      <div className="flex-1 space-y-3 overflow-y-auto">
        {Array.from(groups.entries()).map(([phase, bots]) => (
          <div key={phase}>
            <p className="px-1 text-xs font-semibold text-text-secondary">
              {phase} ({bots.length})
            </p>
            <ul>
              {bots.map((bot) => (
                <li key={bot.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(bot)}
                    className={`flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm ${
                      selectedId === bot.id ? "bg-bg-surfaceHover" : "hover:bg-bg-surfaceHover"
                    }`}
                  >
                    <span className="truncate text-text-primary">
                      {bot.name}
                      {bot.origin_kind === "EXTERNAL_PRODUCTION" ? ` · ${uiStrings.bots.externalF7}` : ""}
                    </span>
                    <SemaphoreBadge state={bot.semaphore_state} />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
