import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";

import LoginPage from "@/routes/LoginPage";
import ResumenPage from "@/routes/ResumenPage";
import RootLayout from "@/routes/RootLayout";

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
const SaludPage = lazy(() => import("@/routes/SaludPage"));
const RiesgoPage = lazy(() => import("@/routes/RiesgoPage"));
const EjecucionPage = lazy(() => import("@/routes/EjecucionPage"));
const EscaladoPage = lazy(() => import("@/routes/EscaladoPage"));
const GraveyardPage = lazy(() => import("@/routes/GraveyardPage"));
const AuditoriaPage = lazy(() => import("@/routes/AuditoriaPage"));
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { index: true, element: <ResumenPage /> },
      { path: "cuentas-ea", element: <CuentasEaPage /> },
      { path: "pipeline", element: <PipelinePage /> },
      { path: "bots", element: <BotsPage /> },
      { path: "portfolio", element: <PortfolioPage /> },
      { path: "salud", element: <SaludPage /> },
      { path: "riesgo", element: <RiesgoPage /> },
      { path: "ejecucion", element: <EjecucionPage /> },
      { path: "escalado", element: <EscaladoPage /> },
      { path: "graveyard", element: <GraveyardPage /> },
      { path: "auditoria", element: <AuditoriaPage /> },
    ],
  },
]);
