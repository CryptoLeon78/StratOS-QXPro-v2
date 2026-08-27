import { useState } from "react";

import { CemeteryCard } from "@/components/domain/graveyard/CemeteryCard";
import { useBots } from "@/hooks/queries/useBots";
import { useCemetery } from "@/hooks/queries/useCemetery";
import uiStrings from "@/styles/ui_strings.es.json";

export default function GraveyardPage() {
  const { data: entries } = useCemetery();
  const { data: bots } = useBots();
  const botById = new Map((bots ?? []).map((bot) => [bot.id, bot]));
  const [profileFilter, setProfileFilter] = useState("");
  const [causeFilter, setCauseFilter] = useState("");

  const profiles = Array.from(new Set((bots ?? []).map((b) => b.profile)));
  const causes = Object.keys(uiStrings.graveyard.causes);

  const filtered = (entries ?? []).filter((entry) => {
    const bot = botById.get(entry.bot_id);
    if (profileFilter && bot?.profile !== profileFilter) return false;
    if (causeFilter && entry.cause !== causeFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4 p-4">
      <p className="rounded-md bg-semantic-warningMuted px-3 py-2 text-sm text-semantic-warning">
        {uiStrings.graveyard.banner}
      </p>
      <div className="flex items-center gap-2">
        <select
          className="rounded-md border border-border-subtle bg-bg-app px-3 py-1.5 text-sm text-text-primary"
          value={profileFilter}
          onChange={(e) => setProfileFilter(e.target.value)}
        >
          <option value="">{uiStrings.graveyard.filterAllProfiles}</option>
          {profiles.map((profile) => (
            <option key={profile} value={profile}>
              {profile}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border border-border-subtle bg-bg-app px-3 py-1.5 text-sm text-text-primary"
          value={causeFilter}
          onChange={(e) => setCauseFilter(e.target.value)}
        >
          <option value="">{uiStrings.graveyard.filterAllCauses}</option>
          {causes.map((cause) => (
            <option key={cause} value={cause}>
              {(uiStrings.graveyard.causes as Record<string, string>)[cause]}
            </option>
          ))}
        </select>
        <span className="text-xs text-text-secondary">
          {filtered.length}/{(entries ?? []).length}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((entry) => (
          <CemeteryCard key={entry.id} entry={entry} bot={botById.get(entry.bot_id)} />
        ))}
      </div>
    </div>
  );
}
