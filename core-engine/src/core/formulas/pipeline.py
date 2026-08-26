"""PARTE 8: gate y proyeccion del pipeline."""

import math
from datetime import datetime

DAYS_PER_WEEK = 7  # constante matematica pura, no un umbral de negocio


def walk_forward_efficiency(oos_return: float, is_return: float) -> float:
    """WFE = OOS/IS; gate F2 >= 0.5 (PARTE 8/6.3). is_return==0 no tiene
    resultado definido -> ZeroDivisionError (division por cero, caso
    obligatorio del pie de PARTE 8)."""
    return oos_return / is_return


def trades_per_week(trades: list[datetime], window_days: int = 30) -> float:
    """Gate 7 del pipeline (PARTE 6.3: >= 2 trades/semana). `trades` ya viene
    acotado por el caller a la ventana relevante; aqui solo se convierte el
    recuento a una tasa semanal."""
    if not trades:
        return 0.0
    return len(trades) / (window_days / DAYS_PER_WEEK)


def decision_eta_days(
    oos_trades: int,
    min_trades: int,
    entered_phase_at: datetime,
    min_days: int,
    freq_week: float,
    now: datetime,
) -> int | None:
    """Proyeccion "Decision habilitada en ~N dias" (PARTE 8). `now` no esta
    en la firma compacta de PARTE 8: sin inyectarlo, la formula leeria el
    reloj del sistema y dejaria de ser pura/determinista (ver ASSUMPTIONS
    G2). freq_week ~0 -> None ("ETA no estimable")."""
    if freq_week <= 0:
        return None
    days_elapsed = (now - entered_phase_at).days
    days_remaining_for_min_days = max(0, min_days - days_elapsed)
    trades_needed = max(0, min_trades - oos_trades)
    days_needed_for_trades = trades_needed / freq_week * DAYS_PER_WEEK
    return math.ceil(max(days_remaining_for_min_days, days_needed_for_trades))
