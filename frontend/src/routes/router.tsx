import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";

import LoginPage from "@/routes/LoginPage";
import ResumenPage from "@/routes/ResumenPage";
import RootLayout from "@/routes/RootLayout";
import RouteError from "@/routes/RouteError";
import uiStrings from "@/styles/ui_strings.es.json";

// Code-splitting por ruta (G9, docs/backlog.md): Resumen y Login se
// cargan EAGER (son lo primero que ve cualquier visitante -- lazy-loadearlas
// solo anadiria un round-trip antes del primer pintado, justo lo contrario
// de "cabecera <2s", criterio de salida de G6). Las otras 10 pestanas SI
// se dividen en su propio chunk -- un operador tipico usa Resumen la
// mayor parte del tiempo, no las 11 a la vez.
const CuentasEaPage = lazy(() => import("@/routes/CuentasEaPage"));
const PipelinePage = lazy(() => import("@/routes/PipelinePage"));
const BotsPage = lazy(() => import("@/routes/BotsPage"));
const PortfolioPage = lazy(() => import("@/routes/PortfolioPage"));
const CorrelacionPage = lazy(() => import("@/routes/CorrelacionPage"));
const SaludPage = lazy(() => import("@/routes/SaludPage"));
const RiesgoPage = lazy(() => import("@/routes/RiesgoPage"));
const EjecucionPage = lazy(() => import("@/routes/EjecucionPage"));
const EscaladoPage = lazy(() => import("@/routes/EscaladoPage"));
const GraveyardPage = lazy(() => import("@/routes/GraveyardPage"));
const AuditoriaPage = lazy(() => import("@/routes/AuditoriaPage"));
// G10 (grupo n): NO anidada bajo RootLayout -- vista dominical no lleva
// AppHeader (EQUITY/P&L/DD) ni TabBar, es "otro modo de revision", no una
// pestana mas.
const DominicalPage = lazy(() => import("@/routes/DominicalPage"));
const SecurityPage = lazy(() => import("@/routes/SecurityPage"));
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/dominical",
    element: (
      <Suspense fallback={<div className="p-6 text-text-secondary">{uiStrings.app.loadingTab}</div>}>
        <DominicalPage />
      </Suspense>
    ),
  },
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <ResumenPage /> },
      { path: "cuentas-ea", element: <CuentasEaPage /> },
      { path: "pipeline", element: <PipelinePage /> },
      { path: "bots", element: <BotsPage /> },
      { path: "portfolio", element: <PortfolioPage /> },
      { path: "correlacion", element: <CorrelacionPage /> },
      { path: "salud", element: <SaludPage /> },
      { path: "riesgo", element: <RiesgoPage /> },
      { path: "ejecucion", element: <EjecucionPage /> },
      { path: "escalado", element: <EscaladoPage /> },
      { path: "graveyard", element: <GraveyardPage /> },
      { path: "auditoria", element: <AuditoriaPage /> },
      { path: "seguridad", element: <SecurityPage /> },
    ],
  },
]);
