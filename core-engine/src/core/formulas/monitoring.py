"""PARTE 8: vigilancia de frecuencia y regimen."""

from core.formulas.types import PHResult, WatchdogState


def watchdog_deviation(
    observed: float,
    expected: float | None,
    tolerance: float = 0.25,
    runaway_factor: float = 3.0,
) -> WatchdogState:
    """PARTE 8: "OK|DEAD|RUNAWAY|OUT_OF_TOLERANCE|INSUFFICIENT_DATA".
    `runaway_factor` no esta en la firma compacta de PARTE 8: sin el, el
    umbral de "desbocado" (SystemConfig `watchdog_runaway_factor=3`)
    quedaria hardcodeado dentro de la formula (P11) (ver ASSUMPTIONS G2)."""
    if expected is None or expected <= 0:
        return WatchdogState.INSUFFICIENT_DATA
    if observed == 0:
        return WatchdogState.DEAD
    if observed > expected * runaway_factor:
        return WatchdogState.RUNAWAY
    deviation = abs(observed - expected) / expected
    if deviation > tolerance:
        return WatchdogState.OUT_OF_TOLERANCE
    return WatchdogState.OK


def page_hinkley(returns: list[float], delta: float, lambda_: float) -> PHResult:
    """Detector de cambio de regimen (autopsia Niobe). Formulacion clasica
    de dos lados (Page 1954/Hinkley 1971): un lado detecta subidas de
    media (u_up, alarma cuando se aleja de su minimo historico mas de
    lambda_), el otro detecta bajadas (u_down, contra su maximo historico)
    -- un cambio de regimen puede ser una mejora o un deterioro (alpha
    decay), no solo un lado (params en config, PARTE 8)."""
    if not returns:
        raise ValueError("page_hinkley: serie vacia")
    mean = 0.0
    u_up = 0.0
    min_up = 0.0
    u_down = 0.0
    max_down = 0.0
    change_point: int | None = None
    statistic = 0.0
    for i, x in enumerate(returns):
        mean += (x - mean) / (i + 1)
        u_up += x - mean - delta
        min_up = min(min_up, u_up)
        u_down += x - mean + delta
        max_down = max(max_down, u_down)
        statistic = max(u_up - min_up, max_down - u_down)
        if change_point is None and statistic > lambda_:
            change_point = i
    return PHResult(
        change_detected=change_point is not None,
        statistic=statistic,
        change_point=change_point,
    )
