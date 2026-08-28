import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// Auto-hospedado (no depende de que el runner de CI tenga 'Inter' instalada a
// nivel de SO): design_tokens.json declara "Inter, system-ui, ..." como
// font.family.sans, pero sin este import el navegador cae al fallback del
// SO -- ubuntu-latest no siempre resuelve la misma fuente entre maquinas
// efimeras del pool, lo que rompia el screenshot-diff de Playwright de forma
// no determinista (10 de 12 specs, mismo commit, resultados distintos entre
// 2 corridas de CI). Solo los 4 pesos que usa font.weight en design_tokens.
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "./styles/index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("root element not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
