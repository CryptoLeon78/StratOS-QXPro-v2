import { Suspense } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { AccountSwitcher } from "@/components/layout/AccountSwitcher";
import { AppHeader } from "@/components/layout/AppHeader";
import { TabBar } from "@/components/layout/TabBar";
import { useAccountScope } from "@/hooks/useAccountScope";
import uiStrings from "@/styles/ui_strings.es.json";
import { useAuthStore } from "@/stores/authStore";

// ADR 0013: "Cuentas" es la unica ruta accesible sin cuenta elegida; el resto
// de pestañas exige una seleccion (se conserva entre sesiones).
const ACCOUNT_FREE_PATHS = new Set(["/cuentas-ea", "/seguridad"]);

export default function RootLayout() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const { accountId, isLoading } = useAccountScope();
  const { pathname } = useLocation();
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }
  if (accountId === null && !isLoading && !ACCOUNT_FREE_PATHS.has(pathname)) {
    return <Navigate to="/cuentas-ea" replace state={{ needAccount: true }} />;
  }

  return (
    <div className="min-h-screen">
      <AppHeader />
      <AccountSwitcher />
      <TabBar />
      {/* G9: las pestanas no-Resumen son lazy (code-splitting por ruta,
      docs/backlog.md) -- este Suspense cubre el hueco entre el clic en la
      TabBar y la descarga del chunk de esa pestana. */}
      <Suspense fallback={<div className="p-6 text-text-secondary">{uiStrings.app.loadingTab}</div>}>
        <Outlet />
      </Suspense>
    </div>
  );
}
