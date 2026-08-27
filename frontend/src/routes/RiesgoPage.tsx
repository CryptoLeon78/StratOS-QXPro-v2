import { ExposureCard } from "@/components/domain/riesgo/ExposureCard";
import { KillSwitchPanel } from "@/components/domain/riesgo/KillSwitchPanel";
import { MonteCarloList } from "@/components/domain/riesgo/MonteCarloList";
import { NewsShieldPanel } from "@/components/domain/riesgo/NewsShieldPanel";
import { TailRiskCard } from "@/components/domain/riesgo/TailRiskCard";

export default function RiesgoPage() {
  return (
    <div className="space-y-4 p-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <KillSwitchPanel />
        <TailRiskCard />
        <ExposureCard />
      </div>
      <NewsShieldPanel />
      <MonteCarloList />
    </div>
  );
}
