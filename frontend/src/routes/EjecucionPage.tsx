import { HeartbeatCard } from "@/components/domain/ejecucion/HeartbeatCard";
import { WatchdogTable } from "@/components/domain/ejecucion/WatchdogTable";
import { TcaPendingCard } from "@/components/domain/TcaPendingCard";

export default function EjecucionPage() {
  return (
    <div className="space-y-4 p-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <HeartbeatCard />
        <TcaPendingCard />
      </div>
      <WatchdogTable />
    </div>
  );
}
