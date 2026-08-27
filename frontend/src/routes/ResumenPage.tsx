import { EquityCard } from "@/components/domain/EquityCard";
import { PipelinePanel } from "@/components/domain/PipelinePanel";
import { RequiresActionPanel } from "@/components/domain/RequiresActionPanel";

export default function ResumenPage() {
  return (
    <div className="space-y-4 p-4">
      <EquityCard />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RequiresActionPanel />
        </div>
        <div>
          <PipelinePanel />
        </div>
      </div>
    </div>
  );
}
