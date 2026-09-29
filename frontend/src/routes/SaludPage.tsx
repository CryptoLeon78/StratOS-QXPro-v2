import { QueryError } from "@/components/domain/QueryError";
import { HealthCard } from "@/components/domain/salud/HealthCard";
import { useHealthBots } from "@/hooks/queries/useHealth";
import uiStrings from "@/styles/ui_strings.es.json";
import { ProvenanceBadge } from "@/components/domain/ProvenanceBadge";

export default function SaludPage() {
  const { data, isLoading, isError, refetch } = useHealthBots();

  // La procedencia se declara SIEMPRE (tambien con la lista vacia) y fuera de la
  // rejilla: dentro ocupaba una celda de las tarjetas.
  return (
    <div className="space-y-4 p-4">
      <ProvenanceBadge />
      {isError && <QueryError onRetry={() => void refetch()} />}
      {!isLoading && !isError && (data ?? []).length === 0 && (
        <div className="text-text-secondary">{uiStrings.salud.emptyState}</div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(data ?? []).map((bot) => (
          <HealthCard key={bot.bot_id} bot={bot} />
        ))}
      </div>
    </div>
  );
}
