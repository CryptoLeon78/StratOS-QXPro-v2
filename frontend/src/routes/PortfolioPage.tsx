import { CorrelationMatrix } from "@/components/domain/portfolio/CorrelationMatrix";
import { MacroStructureCard } from "@/components/domain/portfolio/MacroStructureCard";
import { MicroProfilesTable } from "@/components/domain/portfolio/MicroProfilesTable";

// PARTE 7.5. La seccion "Añade valor real el portfolio?" (comparacion vs
// S&P500, alfa de Jensen) de la captura se omite en G7: ols_alpha_beta
// existe (G2) pero ningun servicio la invoca contra scripts/data/
// sp500_monthly.csv -- docs/backlog.md.
export default function PortfolioPage() {
  return (
    <div className="space-y-4 p-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MacroStructureCard />
        <MicroProfilesTable />
      </div>
      <CorrelationMatrix />
    </div>
  );
}
