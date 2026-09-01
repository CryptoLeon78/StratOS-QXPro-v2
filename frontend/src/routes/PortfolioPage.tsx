import { CorrelationMatrix } from "@/components/domain/portfolio/CorrelationMatrix";
import { MacroStructureCard } from "@/components/domain/portfolio/MacroStructureCard";
import { MicroProfilesTable } from "@/components/domain/portfolio/MicroProfilesTable";
import { PortfolioBenchmarkCard } from "@/components/domain/portfolio/PortfolioBenchmarkCard";
import { ProvenanceBadge } from "@/components/domain/ProvenanceBadge";

// PARTE 7.5. "¿Añade valor real el portfolio?" (G10, services/benchmark.py)
// cierra el ultimo gap de la pestaña -- ver docs/backlog.md.
export default function PortfolioPage() {
  return (
    <div className="space-y-4 p-4">
      <ProvenanceBadge />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MacroStructureCard />
        <MicroProfilesTable />
      </div>
      <CorrelationMatrix />
      <PortfolioBenchmarkCard />
    </div>
  );
}
