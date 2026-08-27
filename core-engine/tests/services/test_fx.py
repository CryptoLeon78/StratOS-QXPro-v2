"""G10 (docs/backlog.md): `FxRate` (esquema desde G1, nunca poblada hasta
ahora por nada del sistema) + `services/fx.py`. HONESTIDAD OPERATIVA
probada aqui tal cual el docstring del modulo: sin tasa disponible,
`latest_rate` devuelve None y `eur_converted_pnl` NUNCA inventa un 1:1 --
la divisa se queda fuera del total, listada en `unconverted_currencies`."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from core.db.models.market import FxRate
from core.services.fx import eur_converted_pnl, latest_rate


class TestLatestRate:
    async def test_returns_none_when_no_rate_stored(self, db_session: object) -> None:
        assert await latest_rate(db_session, base="USD", quote="EUR") is None  # type: ignore[arg-type]

    async def test_returns_the_most_recent_rate(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            FxRate(ts=now - timedelta(days=1), base="USD", quote="EUR", rate=Decimal("0.90"))
        )
        db_session.add(  # type: ignore[attr-defined]
            FxRate(ts=now, base="USD", quote="EUR", rate=Decimal("0.92"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        rate = await latest_rate(db_session, base="USD", quote="EUR")  # type: ignore[arg-type]
        assert rate == Decimal("0.92")

    async def test_direction_matters_no_implicit_inverse(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            FxRate(ts=now, base="EUR", quote="USD", rate=Decimal("1.10"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        # solo hay EUR->USD almacenado; pedir USD->EUR no debe devolverlo invertido
        assert await latest_rate(db_session, base="USD", quote="EUR") is None  # type: ignore[arg-type]
        assert await latest_rate(db_session, base="EUR", quote="USD") == Decimal("1.10")  # type: ignore[arg-type]


class TestEurConvertedPnl:
    async def test_eur_amounts_pass_through_unconverted(self, db_session: object) -> None:
        result = await eur_converted_pnl(db_session, {"EUR": Decimal("100")})  # type: ignore[arg-type]
        assert result.pnl_eur == Decimal("100")
        assert result.unconverted_currencies == frozenset()

    async def test_converts_using_base_currency_to_eur_rate(self, db_session: object) -> None:
        # 1 USD = 0.90 EUR (base=USD, quote=EUR) -> 100 USD = 90 EUR
        db_session.add(  # type: ignore[attr-defined]
            FxRate(ts=datetime.now(UTC), base="USD", quote="EUR", rate=Decimal("0.90"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await eur_converted_pnl(db_session, {"USD": Decimal("100")})  # type: ignore[arg-type]
        assert result.pnl_eur == Decimal("90.00")
        assert result.unconverted_currencies == frozenset()

    async def test_converts_using_inverse_eur_to_currency_rate(self, db_session: object) -> None:
        # solo existe EUR->GBP (1 EUR = 0.85 GBP) -> 85 GBP = 100 EUR (inverso)
        db_session.add(  # type: ignore[attr-defined]
            FxRate(ts=datetime.now(UTC), base="EUR", quote="GBP", rate=Decimal("0.85"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await eur_converted_pnl(db_session, {"GBP": Decimal("85")})  # type: ignore[arg-type]
        assert result.pnl_eur == Decimal("100.00")
        assert result.unconverted_currencies == frozenset()

    async def test_no_rate_excludes_currency_and_reports_it(self, db_session: object) -> None:
        result = await eur_converted_pnl(db_session, {"GBP": Decimal("50")})  # type: ignore[arg-type]
        assert result.pnl_eur == Decimal("0")
        assert result.unconverted_currencies == frozenset({"GBP"})

    async def test_mixes_convertible_and_unconvertible_currencies(self, db_session: object) -> None:
        db_session.add(  # type: ignore[attr-defined]
            FxRate(ts=datetime.now(UTC), base="USD", quote="EUR", rate=Decimal("0.90"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await eur_converted_pnl(  # type: ignore[arg-type]
            db_session, {"EUR": Decimal("10"), "USD": Decimal("100"), "GBP": Decimal("50")}
        )
        assert result.pnl_eur == Decimal("100.00")  # 10 + 90
        assert result.unconverted_currencies == frozenset({"GBP"})
