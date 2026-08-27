import { NavLink } from "react-router-dom";

import uiStrings from "@/styles/ui_strings.es.json";
import { cn } from "@/lib/utils";

// PARTE 11.3: TabBar, 11 tabs, activo subrayado violeta. tokens.component.Tab
// apunta a otros tokens por ruta (activeBorder: "accent.primary", etc.) --
// se resuelven aqui a las clases Tailwind equivalentes en vez de leer el
// path en runtime (una sola vez, sin generalizar un resolver para esto).
const TABS: { to: string; labelKey: keyof typeof uiStrings.tabs }[] = [
  { to: "/", labelKey: "resumen" },
  { to: "/cuentas-ea", labelKey: "cuentasEa" },
  { to: "/pipeline", labelKey: "pipeline" },
  { to: "/bots", labelKey: "bots" },
  { to: "/portfolio", labelKey: "portfolio" },
  { to: "/salud", labelKey: "salud" },
  { to: "/riesgo", labelKey: "riesgo" },
  { to: "/ejecucion", labelKey: "ejecucion" },
  { to: "/escalado", labelKey: "escalado" },
  { to: "/graveyard", labelKey: "graveyard" },
  { to: "/auditoria", labelKey: "auditoria" },
];

export function TabBar() {
  return (
    <nav className="flex gap-1 overflow-x-auto border-b border-border-subtle px-4">
      {TABS.map(({ to, labelKey }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            cn(
              "whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
              isActive
                ? "border-accent-primary text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )
          }
        >
          {uiStrings.tabs[labelKey]}
        </NavLink>
      ))}
    </nav>
  );
}
