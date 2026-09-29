import { EyeOff } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AccountBanner } from "@/components/domain/AccountBanner";
import { HeartbeatCard } from "@/components/domain/ejecucion/HeartbeatCard";
import { WatchdogTable } from "@/components/domain/ejecucion/WatchdogTable";
import { NewsShieldPanel } from "@/components/domain/riesgo/NewsShieldPanel";
import { useAlerts } from "@/hooks/queries/useAlerts";
import { useAuthStore } from "@/stores/authStore";
import uiStrings from "@/styles/ui_strings.es.json";
import { ProvenanceBadge } from "@/components/domain/ProvenanceBadge";

const NEWS_WEEK_AHEAD_HOURS = 24 * 7;

// PARTE 14/16 (grupo n de G10, diseño derivado -- SIN captura de
// referencia, aprobado explicitamente por el operador antes de
// construirla): "revision dominical" (20 min, mercado cerrado) --
// revision TECNICA (errores de EA, desconexiones, ordenes rechazadas) +
// copiar noticias de la semana entrante al filtro horario. PROHIBIDO
// mostrar rentabilidad (criterio de salida literal PARTE 16 #14 -- esta
// pagina NUNCA importa AppHeader/StatCard/formatAmount, verificado con un
// test de contenido real: tests/e2e/vista_dominical.spec.ts confirma que
// las etiquetas EQUITY/P&L DÍA/DRAWDOWN nunca aparecen).
//
// Ruta de nivel superior, NO anidada bajo RootLayout (que siempre renderiza
// el AppHeader con EQUITY/P&L/DD) y NO en la TabBar -- es "otro modo de
// revision", no una pestana mas. Guardia de auth propia, mismo patron que
// RootLayout.
export default function DominicalPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  // useAlerts SIEMPRE se llama (regla de hooks) -- `enabled` internamente
  // via TanStack Query decide si dispara la query, no un early return.
  const { data: eaErrors } = useAlerts("config_drift");

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen">
      <ProvenanceBadge />
      <header className="border-b border-border-subtle px-4 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-text-primary">{uiStrings.dominical.title}</h1>
          <Link to="/" className="text-sm text-text-secondary hover:text-text-primary">
            {uiStrings.dominical.backLink}
          </Link>
        </div>
        <p className="mt-1 text-xs text-text-secondary">{uiStrings.dominical.subtitle}</p>
        <div className="mt-2">
          <AccountBanner />
        </div>
        <p className="mt-2 flex items-center gap-1.5 text-xs text-semantic-warning">
          <EyeOff className="size-3.5" />
          {uiStrings.dominical.noProfitNotice}
        </p>
      </header>

      <div className="space-y-4 p-4">
        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.dominical.eaErrorsTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            {(eaErrors ?? []).length === 0 ? (
              <p className="text-sm text-text-secondary">{uiStrings.dominical.emptyEaErrors}</p>
            ) : (
              <ul className="space-y-2">
                {(eaErrors ?? []).map((alert) => (
                  <li key={alert.id} className="flex items-start gap-2 text-sm">
                    <Badge variant={alert.level === "CRITICA" ? "danger" : "warning"}>
                      {alert.level}
                    </Badge>
                    <div>
                      <p className="text-text-primary">{alert.message}</p>
                      {alert.action_required && (
                        <p className="text-xs text-text-secondary">{alert.action_required}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <div>
          <h2 className="mb-2 text-sm font-semibold text-text-primary">
            {uiStrings.dominical.disconnectionsTitle}
          </h2>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <HeartbeatCard />
            <WatchdogTable />
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{uiStrings.dominical.rejectedOrdersTitle}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-text-secondary">
              {uiStrings.dominical.rejectedOrdersPending}
            </p>
          </CardContent>
        </Card>

        <NewsShieldPanel hours={NEWS_WEEK_AHEAD_HOURS} />
      </div>
    </div>
  );
}
