"""PARTE 13: "beta 0,18 (benchmark scripts/data/sp500_monthly.csv)".

`scripts/data/sp500_monthly.csv` (2021: cifras reales de mercado; 2022+:
sinteticas, ver ASSUMPTIONS G8 -- no hay acceso a datos historicos reales
verificables en este entorno) NO esta cableado a ningun servicio de
core-engine todavia (G7 lo documento como omitido, `docs/backlog.md`) --
`trades_history.py` genera la curva de portfolio de forma INDEPENDIENTE
del benchmark, sin correlacionarla a proposito (regresar la curva del
seed contra este CSV daria una beta espuria, cercana a 0, no 0,18).

Este test verifica lo que SI es verificable sin esa pieza que falta:
`formulas/portfolio.py::ols_alpha_beta` (ya con 100% de cobertura desde
G2) recupera correctamente una beta=0,18 conocida cuando se construye una
relacion CONTROLADA `portfolio = alpha + beta*benchmark + ruido` sobre
los valores REALES de este benchmark -- confirma que el fichero esta bien
formado y es utilizable para ese calculo el dia que exista un consumidor
real (backlog)."""

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from core.formulas.portfolio import ols_alpha_beta

_CSV_PATH = Path(__file__).parent.parent / "data" / "sp500_monthly.csv"
_TARGET_BETA = 0.18
_TARGET_ALPHA = 0.02
_MIN_ROWS = 66  # PARTE 1: "14 meses negativos de 66"


def _load_benchmark() -> pd.Series:
    with _CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return pd.Series([float(row["monthly_return"]) for row in rows])


def test_csv_has_at_least_66_months() -> None:
    benchmark = _load_benchmark()
    assert len(benchmark) >= _MIN_ROWS


def test_ols_alpha_beta_recovers_known_beta_against_benchmark() -> None:
    benchmark = _load_benchmark()
    rng = np.random.default_rng(20260101)
    noise = rng.normal(0.0, 0.005, size=len(benchmark))
    portfolio = _TARGET_ALPHA + _TARGET_BETA * benchmark + pd.Series(noise)

    result = ols_alpha_beta(portfolio, benchmark)

    assert result.beta == pytest.approx(_TARGET_BETA, abs=0.03)
    assert result.n == len(benchmark)
