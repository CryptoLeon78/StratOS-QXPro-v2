// Unico punto de import de doc_app/design_tokens.json (P11: ningun color/
// espaciado suelto en componentes). tailwind.config.ts lo importa para
// generar el theme; los componentes de dominio que necesitan un valor de
// "component" (recetas por componente, no escalares Tailwind) lo leen
// directo de aqui.
import tokens from "../../../doc_app/design_tokens.json";

export type DesignTokens = typeof tokens;

export default tokens;
