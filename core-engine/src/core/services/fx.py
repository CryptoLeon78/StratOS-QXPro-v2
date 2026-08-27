"""G10 (docs/backlog.md): conversion REAL a EUR de un P&L por divisa, a
diferencia de `services/risk.py::exposure_subtotals_by_currency` (G10
tambien, subtotales en unidad NATIVA sin convertir). Se apoya en `FxRate`
(esquema desde G1/PARTE 5.2, columna `(ts, base, quote) -> rate`).

Convencion de `FxRate.rate` (estandar FX, misma que un par de divisas real
tipo EURUSD): `rate` = cuantas unidades de `quote` vale 1 unidad de
`base`. Ej: `base=EUR, quote=USD, rate=1.10` -> 1 EUR = 1.10 USD.

HONESTIDAD OPERATIVA: ningun proceso de este sistema puebla `FxRate`
todavia -- no hay feed de FX en tiempo real ni historico ingerido (mismo
tipo de gap ya documentado para `ea_state` sizing). `latest_rate()`
devuelve `None` mientras la tabla este vacia; `eur_converted_pnl()` NUNCA
inventa una tasa 1:1 -- una divisa sin tasa disponible (en ninguna
direccion) se excluye del total EUR, reportada en
`unconverted_currencies`."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.market import FxRate

_EUR = "EUR"


async def latest_rate(session: AsyncSession, base: str, quote: str) -> Decimal | None:
    """Tasa mas reciente por `ts` para el par `(base, quote)` tal cual
    esta almacenado -- NO intenta la direccion inversa automaticamente
    (eso lo resuelve `eur_converted_pnl`, que sí prueba ambas)."""
    result = await session.execute(
        select(FxRate.rate)
        .where(FxRate.base == base, FxRate.quote == quote)
        .order_by(FxRate.ts.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@dataclass(frozen=True)
class EurConvertedExposure:
    pnl_eur: Decimal
    unconverted_currencies: frozenset[str]


async def eur_converted_pnl(
    session: AsyncSession, pnl_by_currency: dict[str, Decimal]
) -> EurConvertedExposure:
    """Convierte cada entrada de `pnl_by_currency` a EUR y suma. `EUR`
    pasa directo (sin lookup). Para cada otra divisa `X`, intenta primero
    `latest_rate(base=X, quote=EUR)` (multiplicar) y si no existe
    `latest_rate(base=EUR, quote=X)` (dividir) -- sin ninguna de las dos,
    la divisa se excluye del total y se reporta en
    `unconverted_currencies`, nunca se asume 1:1."""
    total_eur = Decimal("0")
    unconverted: set[str] = set()

    for currency, amount in pnl_by_currency.items():
        if currency == _EUR:
            total_eur += amount
            continue

        direct = await latest_rate(session, base=currency, quote=_EUR)
        if direct is not None:
            total_eur += amount * direct
            continue

        inverse = await latest_rate(session, base=_EUR, quote=currency)
        if inverse is not None:
            total_eur += amount / inverse
            continue

        unconverted.add(currency)

    return EurConvertedExposure(pnl_eur=total_eur, unconverted_currencies=frozenset(unconverted))
