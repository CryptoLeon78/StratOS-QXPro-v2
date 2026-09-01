import { HealthCard } from "@/components/domain/salud/HealthCard";
import { useHealthBots } from "@/hooks/queries/useHealth";
import uiStrings from "@/styles/ui_strings.es.json";
import { ProvenanceBadge } from "@/components/domain/ProvenanceBadge";

export default function SaludPage() {
  const { data, isLoading } = useHealthBots();

  if (!isLoading && (data ?? []).length === 0) {
    return <div className="p-4 text-text-secondary">{uiStrings.salud.emptyState}</div>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
      <ProvenanceBadge />
      {(data ?? []).map((bot) => (
        <HealthCard key={bot.bot_id} bot={bot} />
      ))}
    </div>
  );
}
