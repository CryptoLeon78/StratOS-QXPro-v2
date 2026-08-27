import { Suspense } from "react";
import { Navigate, Outlet } from "react-router-dom";

import { AppHeader } from "@/components/layout/AppHeader";
import { TabBar } from "@/components/layout/TabBar";
import uiStrings from "@/styles/ui_strings.es.json";
import { useAuthStore } from "@/stores/authStore";

export default function RootLayout() {
  const accessToken = useAuthStore((state) => state.accessToken);
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen">
      <AppHeader />
      <TabBar />
      {/* G9: las 10 pestanas no-Resumen son lazy (code-splitting por ruta,
      docs/backlog.md) -- este Suspense cubre el hueco entre el clic en la
      TabBar y la descarga del chunk de esa pestana. */}
      <Suspense fallback={<div className="p-6 text-text-secondary">{uiStrings.app.loadingTab}</div>}>
        <Outlet />
      </Suspense>
    </div>
  );
}
