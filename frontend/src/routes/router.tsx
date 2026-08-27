import { createBrowserRouter } from "react-router-dom";

import AuditoriaPage from "@/routes/placeholders/AuditoriaPage";
import BotsPage from "@/routes/placeholders/BotsPage";
import CuentasEaPage from "@/routes/placeholders/CuentasEaPage";
import EjecucionPage from "@/routes/placeholders/EjecucionPage";
import EscaladoPage from "@/routes/placeholders/EscaladoPage";
import GraveyardPage from "@/routes/placeholders/GraveyardPage";
import PipelinePage from "@/routes/placeholders/PipelinePage";
import PortfolioPage from "@/routes/PortfolioPage";
import RiesgoPage from "@/routes/placeholders/RiesgoPage";
import SaludPage from "@/routes/SaludPage";
import LoginPage from "@/routes/LoginPage";
import ResumenPage from "@/routes/ResumenPage";
import RootLayout from "@/routes/RootLayout";

// 11 pestanas (PARTE 7): solo Resumen tiene contenido real en G6, el resto
// son placeholders navegables que G7 sustituye una por unidad de commit.
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
