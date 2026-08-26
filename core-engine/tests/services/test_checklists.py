from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from core.db.enums import ChecklistType
from core.services.checklists import (
    DEFAULT_CHECKLIST_CATALOG,
    ChecklistCatalog,
    period_key_for,
    sign_item,
)

CATALOG = ChecklistCatalog()


class TestPeriodKeyFor:
    def test_sunday_uses_iso_week(self) -> None:
        assert period_key_for(ChecklistType.SUNDAY, datetime(2026, 8, 23, tzinfo=UTC)) == "2026-W34"

    def test_biweekly_splits_month_in_two(self) -> None:
        assert period_key_for(ChecklistType.BIWEEKLY, datetime(2026, 8, 10, tzinfo=UTC)) == (
            "2026-08-H1"
        )
        assert period_key_for(ChecklistType.BIWEEKLY, datetime(2026, 8, 20, tzinfo=UTC)) == (
            "2026-08-H2"
        )

    def test_monthly_is_year_month(self) -> None:
        assert period_key_for(ChecklistType.MONTHLY, datetime(2026, 8, 1, tzinfo=UTC)) == "2026-08"

    def test_quarterly_matches_impulses_quarter_format(self) -> None:
        assert period_key_for(ChecklistType.QUARTERLY, datetime(2026, 8, 10, tzinfo=UTC)) == (
            "2026-Q3"
        )

    def test_annual_is_year(self) -> None:
        assert period_key_for(ChecklistType.ANNUAL, datetime(2026, 8, 10, tzinfo=UTC)) == "2026"

    @given(days_later=st.integers(min_value=0, max_value=3650))
    def test_monthly_key_is_never_lexicographically_smaller_for_a_later_date(
        self, days_later: int
    ) -> None:
        base = datetime(2020, 1, 1, tzinfo=UTC)
        later = base + timedelta(days=days_later)
        assert period_key_for(ChecklistType.MONTHLY, later) >= period_key_for(
            ChecklistType.MONTHLY, base
        )


class TestSignItem:
    async def test_partial_signature_returns_none(self, db_session: object) -> None:
        now = datetime(2026, 8, 23, tzinfo=UTC)
        first_item = DEFAULT_CHECKLIST_CATALOG[ChecklistType.SUNDAY][0]
        result = await sign_item(  # type: ignore[arg-type]
            db_session, ChecklistType.SUNDAY, first_item, "ivan", CATALOG, now
        )
        assert result is None

    async def test_completing_the_catalog_persists_immutable_run(self, db_session: object) -> None:
        now = datetime(2026, 8, 23, tzinfo=UTC)
        items = DEFAULT_CHECKLIST_CATALOG[ChecklistType.SUNDAY]
        run = None
        for item in items:
            run = await sign_item(  # type: ignore[arg-type]
                db_session, ChecklistType.SUNDAY, item, "ivan", CATALOG, now
            )
        assert run is not None
        assert run.completed is True
        assert set(run.items.keys()) == set(items)
        assert run.signature_hash is not None

    async def test_rejects_an_item_outside_the_catalog(self, db_session: object) -> None:
        now = datetime(2026, 8, 23, tzinfo=UTC)
        with pytest.raises(ValueError, match="catalogo"):
            await sign_item(  # type: ignore[arg-type]
                db_session, ChecklistType.SUNDAY, "item inventado", "ivan", CATALOG, now
            )

    async def test_rejects_signing_after_the_period_is_already_closed(
        self, db_session: object
    ) -> None:
        now = datetime(2026, 8, 23, tzinfo=UTC)
        items = DEFAULT_CHECKLIST_CATALOG[ChecklistType.SUNDAY]
        for item in items:
            await sign_item(  # type: ignore[arg-type]
                db_session, ChecklistType.SUNDAY, item, "ivan", CATALOG, now
            )
        with pytest.raises(ValueError, match="inmutable"):
            await sign_item(  # type: ignore[arg-type]
                db_session, ChecklistType.SUNDAY, items[0], "ivan", CATALOG, now
            )
