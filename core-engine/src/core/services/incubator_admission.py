"""Gate de admision a Incubadora: los dos criterios de descorrelacion.

El tope por simbolo/timeframe y la correlacion entre curvas miden cosas distintas, y ninguno
sustituye al otro:

- **Estructural** -- no ocho bots del mismo par y marco temporal. Aunque sus reglas difieran,
  comparten mercado y horizonte: el kill-switch los veria caer juntos. Es un tope barato de
  aplicar y no necesita que el candidato haya operado.
- **Estadistico** -- dos `AUDCAD/H4` con correlacion 0,2 diversifican; dos con 0,9 no, aunque
  el tope estructural los deje pasar. Y al reves: dos instrumentos distintos con correlacion
  0,95 tampoco diversifican, aunque ningun tope por simbolo los toque. El tope estructural
  *aproxima* la diversidad; la correlacion la *mide*.

Un candidato de Analisis no ha operado todavia, asi que su serie de PnL sale del backtest:
la correlacion es backtest-contra-real, no real-contra-real. El gate la usa como senal y lo
declara en la evidencia, en vez de presentarla como equivalente a una medida entre bots vivos.

Fail-closed en las dos direcciones: sin serie del candidato o de un ocupante no se puede medir
descorrelacion, y admitir a ciegas romperia el criterio que este gate existe para aplicar.

Los umbrales viven en `config/operational_prefilter.json` (`incubator_admission`), no aqui.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdmissionConfig:
    max_per_symbol_timeframe: int
    max_concurrent: int
    max_abs_correlation: float


@dataclass(frozen=True)
class IncubatorSlot:
    """Un bot ya dentro de la Incubadora, con la serie contra la que se compara."""

    bot_id: int
    symbol: str
    timeframe: str
    pnl_series: list[float]


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    reason: str | None
    correlated_with: int | None
    max_abs_correlation: float | None
    config: AdmissionConfig

    def as_evidence(self) -> dict[str, Any]:
        """Forma serializable para el registro append-only de admision."""
        return {
            "admitted": self.admitted,
            "reason": self.reason,
            "correlated_with": self.correlated_with,
            "max_abs_correlation": self.max_abs_correlation,
            "config": {
                "max_per_symbol_timeframe": self.config.max_per_symbol_timeframe,
                "max_concurrent": self.config.max_concurrent,
                "max_abs_correlation": self.config.max_abs_correlation,
            },
        }


def _pearson(a: list[float], b: list[float]) -> float | None:
    """Correlacion de Pearson sobre el tramo comun. `None` cuando es indefinida.

    Dos series de distinta longitud se alinean por la cola: los ultimos `n` valores de cada
    una, que es el tramo en el que ambas existen. Una serie constante da varianza cero y
    Pearson indefinida -- se devuelve `None` en vez de un 0 que se leeria como
    "descorrelacionadas", que es justo lo contrario de lo que significa no poder medirlo.
    """
    n = min(len(a), len(b))
    if n < 2:
        return None
    x, y = a[-n:], b[-n:]
    try:
        return statistics.correlation(x, y)
    except statistics.StatisticsError:
        return None


def evaluate_admission(
    *,
    symbol: str,
    timeframe: str,
    pnl_series: list[float],
    occupied: list[IncubatorSlot],
    config: AdmissionConfig,
) -> AdmissionDecision:
    """Decide si un candidato entra en Incubadora, y por que no si no entra.

    El orden importa: primero la capacidad, luego el criterio estructural y solo despues el
    estadistico. Si el bucket esta lleno da igual lo que diga la correlacion, y reportar el
    motivo que de verdad bloquea evita que el operador persiga la causa equivocada.
    """

    def decision(
        admitted: bool,
        reason: str | None = None,
        correlated_with: int | None = None,
        max_abs: float | None = None,
    ) -> AdmissionDecision:
        return AdmissionDecision(
            admitted=admitted,
            reason=reason,
            correlated_with=correlated_with,
            max_abs_correlation=max_abs,
            config=config,
        )

    if len(occupied) >= config.max_concurrent:
        return decision(False, "INCUBATOR_FULL")

    mismo_bucket = [
        slot for slot in occupied if slot.symbol == symbol and slot.timeframe == timeframe
    ]
    if len(mismo_bucket) >= config.max_per_symbol_timeframe:
        return decision(False, "SYMBOL_TIMEFRAME_CAP")

    if not occupied:
        # Nada con lo que correlacionar: el primero entra por capacidad, no por medida.
        return decision(True)

    if len(pnl_series) < 2:
        return decision(False, "NO_SERIES_FOR_CORRELATION")

    peor_correlacion: float | None = None
    peor_bot: int | None = None
    for slot in occupied:
        correlacion = _pearson(pnl_series, slot.pnl_series)
        if correlacion is None:
            # Un ocupante sin serie comparable no se ignora: no poder medir no es descorrelar.
            return decision(False, "OCCUPANT_WITHOUT_SERIES", correlated_with=slot.bot_id)
        absoluta = abs(correlacion)
        if peor_correlacion is None or absoluta > peor_correlacion:
            peor_correlacion, peor_bot = absoluta, slot.bot_id

    assert peor_correlacion is not None  # occupied no vacio y ningun None: siempre hay peor
    if peor_correlacion > config.max_abs_correlation:
        # Se mide en valor absoluto: una correlacion -0,95 no es diversificacion, es la misma
        # apuesta al reves, y el kill-switch la ve caer cuando la otra sube.
        return decision(
            False,
            "CORRELATED_WITH_OCCUPANT",
            correlated_with=peor_bot,
            max_abs=peor_correlacion,
        )
    return decision(True, max_abs=peor_correlacion)
