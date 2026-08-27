import { Badge } from "@/components/ui/badge";
import uiStrings from "@/styles/ui_strings.es.json";

// CemeteryCause (core/db/enums.py) -- pestana Graveyard (7.8), etiquetas
// espanolas exactas de la captura.
export function CauseBadge({ cause }: { cause: string }) {
  const label = (uiStrings.graveyard.causes as Record<string, string>)[cause] ?? cause;
  return <Badge variant="outline">{label}</Badge>;
}
