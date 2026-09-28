import { Bell, Wifi, WifiOff } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { SemaphoreBadge } from "@/components/domain/SemaphoreBadge";
import { StatCard } from "@/components/domain/StatCard";
import { HEADER_SUMMARY_QUERY_KEY, useHeaderSummary } from "@/hooks/queries/useHeaderSummary";
import { useWsTopic } from "@/hooks/useWsTopic";
import { decodeJwtPayload } from "@/lib/jwt";
import { formatAmount, formatPercent, formatSignedAmount } from "@/lib/formatters";
import { interpolate } from "@/lib/i18n";
import { useAuthStore } from "@/stores/authStore";
import uiStrings from "@/styles/ui_strings.es.json";

// PARTE 7.1: cabecera global persistente, 6 StatCard, en TODAS las
// pestanas. Contra GET /api/v1/header/summary (refetch cada 5s hasta que
// el commit del cliente WS lo sustituya por invalidacion via evento).
export function AppHeader() {
  const { data, isLoading } = useHeaderSummary();
  // `isLoading` de TanStack Query solo cubre la carga INICIAL: si un
  // refetch posterior (poll de 5s o invalidacion por WS) falla -- p.ej. el
  // access token expira y /auth/refresh tambien devuelve 401 (ver
  // api/client.ts) -- `isLoading` se queda en `false` aunque `data` vuelva
  // a `undefined`. RootLayout redirige a /login al limpiar la sesion, pero
  // esa actualizacion de Zustand y esta de React Query son dos fuentes
  // reactivas independientes: en el commit donde gana la segunda, este
  // componente puede renderizar todavia con `data` vacio. `ready` cubre
  // los dos casos (cargando O sin dato por cualquier motivo) con el mismo
  // placeholder "-" que ya existia para la carga inicial, en vez de asumir
  // `data` presente. Hallazgo real: TypeError en produccion leyendo
  // `equity_eur` de `undefined`.
  const ready = !isLoading && data !== undefined;
  // equity/alerts: los 2 topics de PARTE 9.3 que afectan a algun campo del
  // header (equity_eur/pnl_* vs alerts/pending_decisions).
  useWsTopic("equity", HEADER_SUMMARY_QUERY_KEY);
  useWsTopic("alerts", HEADER_SUMMARY_QUERY_KEY);
  const accessToken = useAuthStore((state) => state.accessToken);
  const claims = accessToken ? decodeJwtPayload(accessToken) : null;
  const roleLabel = claims
    ? (uiStrings.header.roleLabels as Record<string, string>)[claims.role] ?? claims.role
    : "";
  const isG12Demo = import.meta.env.VITE_OPERATIONAL_MODE === "g12_demo";
  const isOperational = import.meta.env.VITE_OPERATIONAL_MODE === "operational";

  return (
    <header className="border-b border-border-subtle">
      <div className="flex items-center justify-between px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">{uiStrings.app.title}</h1>
        </div>
        <div className="flex items-center gap-3">
          {isG12Demo && <Badge variant="warning">{uiStrings.app.g12DemoLabel}</Badge>}
          {isOperational && <Badge variant="outline">{uiStrings.app.operationalLabel}</Badge>}
          {/* G10 (grupo n): unico punto de entrada a /dominical -- no es
          una pestana mas (no esta en TabBar), enlace discreto junto al
          badge de rol. */}
          <Link to="/dominical" className="text-xs text-text-secondary hover:text-text-primary">
            {uiStrings.dominical.headerLink}
          </Link>
          <Link to="/seguridad" className="text-xs text-text-secondary hover:text-text-primary">
            {uiStrings.security.headerLink}
          </Link>
          {roleLabel && <Badge variant="default">{roleLabel}</Badge>}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 px-4 pb-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard
          label={uiStrings.header.equity}
          value={!ready ? "—" : `${formatAmount(data.equity_eur)}`}
        />
        <StatCard
          label={uiStrings.header.pnlDay}
          value={!ready ? "—" : formatSignedAmount(data.pnl_day)}
          valueClassName={
            ready && Number(data.pnl_day) < 0 ? "text-pnl-negative" : "text-pnl-positive"
          }
          subtext={
            ready &&
            interpolate(uiStrings.header.weekMonth, {
              week: formatAmount(data.pnl_week),
              month: formatAmount(data.pnl_month),
            })
          }
        />
        <StatCard
          label={uiStrings.header.drawdown}
          value={!ready ? "—" : formatPercent(data.portfolio_dd_pct)}
          subtext={
            ready &&
            (data.ks_level === 0
              ? uiStrings.header.ksInactive
              : interpolate(uiStrings.header.ksActive, { level: data.ks_level }))
          }
        />
        <StatCard
          label={uiStrings.header.semaphoreGlobal}
          value={!ready ? "—" : <SemaphoreBadge state={data.global_semaphore} />}
        />
        <StatCard
          label={uiStrings.header.mt}
          value={
            !ready ? (
              "—"
            ) : (
              <span className="flex items-center gap-1.5">
                {data.mt_connected ? (
                  <Wifi className="size-4 text-semantic-success" />
                ) : (
                  <WifiOff className="size-4 text-semantic-danger" />
                )}
                {data.mt_connected ? uiStrings.header.connected : uiStrings.header.disconnected}
              </span>
            )
          }
          subtext={
            ready && interpolate(uiStrings.header.openPositions, { count: data.open_positions })
          }
        />
        <StatCard
          label={uiStrings.header.alerts}
          value={
            !ready ? (
              "—"
            ) : (
              <span className="flex items-center gap-1.5">
                <Bell className="size-4 text-text-secondary" />
                {data.alerts}
              </span>
            )
          }
          subtext={
            ready &&
            interpolate(uiStrings.header.pendingDecisions, { count: data.pending_decisions })
          }
        />
      </div>
      {/* G9: el badge SIEMPRE ocupa su fila (invisible en vez de ausente
      cuando no aplica) -- antes se montaba/desmontaba con
      data_stale_seconds, desplazando verticalmente TODO el contenido de
      debajo (TabBar + pestaña activa) cada vez que la frescura de los
      datos cruzaba el umbral entre la captura del baseline de Playwright
      y la corrida del test -- una carrera de tiempo real que rompio
      cuentas_ea.spec.ts en CI 2 veces (ver ASSUMPTIONS G9-06/G9-07);
      ninguna mascara puede compensar un cambio de altura de pagina, solo
      una altura estable lo resuelve de raiz. */}
      <div className="px-4 pb-3" data-testid="data-stale-badge">
        <Badge
          variant="warning"
          className={!ready || data.data_stale_seconds === null ? "invisible" : undefined}
        >
          {interpolate(uiStrings.header.dataStale, {
            minutes:
              ready && data.data_stale_seconds !== null
                ? Math.round(data.data_stale_seconds / 60)
                : 0,
          })}
        </Badge>
      </div>
    </header>
  );
}
