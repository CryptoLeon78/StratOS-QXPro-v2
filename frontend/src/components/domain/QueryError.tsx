import { Button } from "@/components/ui/button";
import uiStrings from "@/styles/ui_strings.es.json";

// Estado de error compartido: una consulta fallida se declara (con reintento)
// en vez de dejar la tarjeta vacia como si no hubiera datos.
export function QueryError({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" className="flex items-center gap-3 text-sm text-semantic-danger">
      <span>{uiStrings.app.queryError}</span>
      <Button variant="outline" size="sm" onClick={onRetry}>
        {uiStrings.app.retry}
      </Button>
    </div>
  );
}
