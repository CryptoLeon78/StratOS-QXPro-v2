import { usePipelineGateThresholds } from "@/hooks/queries/useConfig";
import uiStrings from "@/styles/ui_strings.es.json";
import type { PipelineCandidate } from "@/api/endpoints/pipeline";

type Criterion = { key: string; value: number | null; threshold: number; passed: boolean };

// PARTE 6.3, 7 criterios reales del gate automatico -- recalculados aqui a
// partir de los campos crudos ya presentes en CandidateResponse + los
// umbrales del nuevo GET /config/pipeline-gate, con la MISMA logica que
// state_machines/pipeline.py::evaluate_pipeline_gate (mayor-que/menor-que,
// no se inventa banda ni redondeo). ADR: la captura muestra un desglose
// distinto (Sortino/Asymmetry) que no coincide con los 7 criterios
// realmente implementados -- se prioriza el codigo (fuente de verdad #1)
// sobre el mockup visual (fuente de verdad #2).
function computeCriteria(
  candidate: PipelineCandidate,
  thresholds: {
    pf: number;
    exp: number;
    sharpe: number;
    maxdd: number;
    min_trades: number;
    min_days: number;
    min_freq_week: number;
  }
): Criterion[] {
  return [
    {
      key: "profit_factor",
      value: candidate.profit_factor,
      threshold: thresholds.pf,
      passed: (candidate.profit_factor ?? -Infinity) > thresholds.pf,
    },
    {
      key: "expectancy_r",
      value: candidate.expectancy_r,
      threshold: thresholds.exp,
      passed: (candidate.expectancy_r ?? -Infinity) > thresholds.exp,
    },
    {
      key: "sharpe",
      value: candidate.sharpe,
      threshold: thresholds.sharpe,
      passed: (candidate.sharpe ?? -Infinity) > thresholds.sharpe,
    },
    {
      key: "max_dd_pct",
      value: candidate.max_dd_pct !== null ? Number(candidate.max_dd_pct) : null,
      threshold: thresholds.maxdd,
      passed:
        candidate.max_dd_pct !== null && Number(candidate.max_dd_pct) < thresholds.maxdd,
    },
    {
      key: "sample",
      value: candidate.oos_trades,
      threshold: thresholds.min_trades,
      passed: candidate.oos_trades >= thresholds.min_trades,
    },
    {
      key: "incubation",
      value: candidate.incubation_days,
      threshold: thresholds.min_days,
      passed: candidate.incubation_days >= thresholds.min_days,
    },
    {
      key: "frequency",
      value: candidate.trades_per_week,
      threshold: thresholds.min_freq_week,
      passed: (candidate.trades_per_week ?? -Infinity) >= thresholds.min_freq_week,
    },
  ];
}

export function GateChecklist({ candidate }: { candidate: PipelineCandidate }) {
  const { data: thresholds } = usePipelineGateThresholds();
  if (!thresholds) return null;

  const criteria = computeCriteria(candidate, thresholds);
  const labels = uiStrings.pipeline.criteria as Record<string, string>;

  return (
    <ul className="space-y-1 text-xs">
      {criteria.map((criterion) => (
        <li key={criterion.key} className="flex items-center justify-between gap-2">
          <span className="text-text-secondary">{labels[criterion.key]}</span>
          <span className={criterion.passed ? "text-semantic-success" : "text-semantic-danger"}>
            {criterion.value === null ? "—" : criterion.value} / {criterion.threshold}{" "}
            {criterion.passed ? "✓" : "✗"}
          </span>
        </li>
      ))}
    </ul>
  );
}
