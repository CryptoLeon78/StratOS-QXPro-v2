import { CorrelationMatrix } from "@/components/domain/portfolio/CorrelationMatrix";

// ADR 0014: la matriz de correlacion sale de Portfolio y pasa a pestaña propia;
// muestra dos matrices (teorica/backtest y observada/real) de la cuenta activa.
export default function CorrelacionPage() {
  return (
    <div className="space-y-4 p-4">
      <CorrelationMatrix />
    </div>
  );
}
