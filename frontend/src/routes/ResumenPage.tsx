import { EquityCard } from "@/components/domain/EquityCard";
import { RequiresActionPanel } from "@/components/domain/RequiresActionPanel";

// Panel "Pipeline" se anade en el commit siguiente de G6.
export default function ResumenPage() {
  return (
    <div className="space-y-4 p-4">
      <EquityCard />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RequiresActionPanel />
        </div>
      </div>
    </div>
  );
}
