import uiStrings from "@/styles/ui_strings.es.json";

// Esqueleto de ruta (commit "router esqueleto") -- el contenido real (6
// StatCard, curva de equity, panel de decisiones, panel de pipeline) se
// construye en los commits siguientes de G6.
export default function ResumenPage() {
  return <div className="p-4 text-text-secondary">{uiStrings.tabs.resumen}</div>;
}
