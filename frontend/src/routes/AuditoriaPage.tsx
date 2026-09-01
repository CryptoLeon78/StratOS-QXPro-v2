import { ShieldCheck } from "lucide-react";

import { ContinuityCard } from "@/components/domain/auditoria/ContinuityCard";
import { ReconciliationCard } from "@/components/domain/auditoria/ReconciliationCard";
import { SealsCard } from "@/components/domain/auditoria/SealsCard";
import uiStrings from "@/styles/ui_strings.es.json";
import { ProvenanceBadge } from "@/components/domain/ProvenanceBadge";

// PARTE 7.9. El banner "Verificado" es una afirmacion estatica sobre la
// arquitectura de ingesta (datos recibidos directamente del terminal, sin
// intervencion manual) -- no depende de ningun campo de API, es
// literalmente cierto por diseno del sistema (P1/P6), igual que el
// disclaimer de SealsCard.
export default function AuditoriaPage() {
  return (
    <div className="space-y-4 p-4">
      <ProvenanceBadge />
      <div className="flex items-center gap-2 rounded-md border-l-2 border-l-semantic-success bg-bg-surface px-3 py-2">
        <ShieldCheck className="size-5 text-semantic-success" />
        <div>
          <p className="text-sm font-semibold text-text-primary">{uiStrings.auditoria.verifiedTitle}</p>
          <p className="text-xs text-text-secondary">{uiStrings.auditoria.verifiedSubtitle}</p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ReconciliationCard />
        <ContinuityCard />
      </div>
      <SealsCard />
    </div>
  );
}
