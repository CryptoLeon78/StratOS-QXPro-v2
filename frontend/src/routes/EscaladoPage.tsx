import { CurrentPhaseCard } from "@/components/domain/escalado/CurrentPhaseCard";
import { MonthlyEvolutionTable } from "@/components/domain/escalado/MonthlyEvolutionTable";
import { PhasesTable } from "@/components/domain/escalado/PhasesTable";

export default function EscaladoPage() {
  return (
    <div className="space-y-4 p-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CurrentPhaseCard />
        <PhasesTable />
      </div>
      <MonthlyEvolutionTable />
    </div>
  );
}
