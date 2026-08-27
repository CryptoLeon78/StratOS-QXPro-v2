"""G10 (docs/backlog.md): "¿Añade valor real el portfolio?" (pestaña
Portfolio, 7.3) -- compara la curva de equity real de portfolio contra el
S&P 500 (`scripts/data/sp500_monthly.csv`, 72 meses desde G8). Reutiliza
`ols_alpha_beta()` (formulas/portfolio.py, G2, 100% cobertura) para
alpha/beta/t_stat/p_value; CAGR/Information Ratio/Batting Average/
Up-Down capture son definiciones estandar de la industria, no formulas
contractuales de PARTE 8.

CAVEAT documentado en `scripts/tests/test_sp500_benchmark.py` (G8): el
CSV solo tiene datos de mercado reales para 2021, el resto es sintetico
(sin acceso a datos historicos reales verificables en este entorno) --
comparar contra el seed real de este sistema puede dar una correlacion
espuria, no es un bug del calculo."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.accounts import Account
from core.db.models.market import EquitySnapshot
from core.formulas.portfolio import MIN_OLS_POINTS, ols_alpha_beta

_MONTHS_PER_YEAR = 12
_DEFAULT_CSV_PATH = Path(__file__).resolve().parents[4] / "scripts" / "data" / "sp500_monthly.csv"


async def portfolio_monthly_returns(session: AsyncSession, now: datetime) -> pd.Series:
    """Retornos mensuales reales de portfolio: ultimo `EquitySnapshot` de
    cada mes calendario, solo cuentas REALES (nunca DEMO, P6.2)."""
    rows = (
        await session.execute(
            select(EquitySnapshot.ts, EquitySnapshot.equity)
            .join(Account, Account.id == EquitySnapshot.account_id)
            .where(Account.is_demo.is_(False))
            .order_by(EquitySnapshot.ts)
        )
    ).all()
    if not rows:
        return pd.Series(dtype=float)

    frame = pd.DataFrame(rows, columns=["ts", "equity"])
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True).dt.tz_localize(None)
    frame["equity"] = frame["equity"].astype(float)
    monthly = frame.set_index("ts")["equity"].resample("ME").last()
    return monthly.pct_change().dropna()


def load_sp500_monthly(csv_path: Path | None = None) -> pd.Series:
    """Lee `scripts/data/sp500_monthly.csv` (columnas `date,monthly_return`)
    como `pd.Series` indexada por fecha de fin de mes. `csv_path=None` usa
    la ruta resuelta contra la raiz del repo (`Settings.benchmark_csv_path`
    la sobrescribe si esta definida, ver `routers/portfolio.py`)."""
    path = csv_path if csv_path is not None else _DEFAULT_CSV_PATH
    frame = pd.read_csv(path, parse_dates=["date"])
    return frame.set_index("date")["monthly_return"].astype(float)


@dataclass(frozen=True)
class BenchmarkComparison:
    n_months: int
    cagr_portfolio: float
    cagr_benchmark: float
    alpha: float
    beta: float
    t_stat: float
    p_value: float
    information_ratio: float
    batting_average: float
    up_capture: float | None
    down_capture: float | None


def _cagr_pct(monthly_returns: pd.Series, n_months: int) -> float:
    total_growth = float((1 + monthly_returns).to_numpy().prod())
    years = n_months / _MONTHS_PER_YEAR
    if years <= 0 or total_growth <= 0:
        return 0.0
    return float(total_growth ** (1 / years) - 1) * 100


def compare_to_benchmark(
    portfolio_monthly: pd.Series, benchmark_monthly: pd.Series
) -> BenchmarkComparison | None:
    """Alinea ambas series por fecha (solo meses en comun -- una serie mas
    larga que la otra no produce filas fantasma) y calcula el set completo
    de metricas. Menos de `MIN_OLS_POINTS` meses solapados, o ningun
    solape -- `None` (mismo gate que `ols_alpha_beta`, sin grados de
    libertad suficientes para una regresion con sentido)."""
    aligned = pd.concat(
        [portfolio_monthly.rename("portfolio"), benchmark_monthly.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    n = len(aligned)
    if n < MIN_OLS_POINTS:
        return None

    alpha_beta = ols_alpha_beta(aligned["portfolio"], aligned["benchmark"])

    excess = aligned["portfolio"] - aligned["benchmark"]
    std = float(excess.std())
    information_ratio = float(excess.mean() / std * (_MONTHS_PER_YEAR**0.5)) if std > 0 else 0.0

    batting_average = float((aligned["portfolio"] > aligned["benchmark"]).mean() * 100)

    up_months = aligned[aligned["benchmark"] > 0]
    down_months = aligned[aligned["benchmark"] < 0]
    up_capture = (
        float(up_months["portfolio"].mean() / up_months["benchmark"].mean() * 100)
        if len(up_months) > 0 and up_months["benchmark"].mean() != 0
        else None
    )
    down_capture = (
        float(down_months["portfolio"].mean() / down_months["benchmark"].mean() * 100)
        if len(down_months) > 0 and down_months["benchmark"].mean() != 0
        else None
    )

    return BenchmarkComparison(
        n_months=n,
        cagr_portfolio=_cagr_pct(aligned["portfolio"], n),
        cagr_benchmark=_cagr_pct(aligned["benchmark"], n),
        alpha=alpha_beta.alpha,
        beta=alpha_beta.beta,
        t_stat=alpha_beta.t_stat,
        p_value=alpha_beta.p_value,
        information_ratio=information_ratio,
        batting_average=batting_average,
        up_capture=up_capture,
        down_capture=down_capture,
    )
