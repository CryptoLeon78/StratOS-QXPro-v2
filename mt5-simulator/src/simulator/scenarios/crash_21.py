"""PARTE 13, identificador literal contractual: "`crash_21` (DD 21% para
kill-switch)". Curva de equity que cae 21% desde un pico, para ejercitar
la escalera L1-L4 del kill-switch (8/12/15/20%, PARTE 6.2) -- 21% supera
incluso L4."""

from decimal import Decimal

from connector.protocol import AccountInfoDTO

from simulator.client import TimelineStep

PEAK_EQUITY = Decimal("100000.00")
CRASH_RATIO = Decimal("0.79")  # equity final = 79% del pico -> DD del 21%


def build_crash_21_timeline() -> list[TimelineStep]:
    crashed_equity = (PEAK_EQUITY * CRASH_RATIO).quantize(Decimal("0.01"))
    return [
        TimelineStep(
            elapsed_seconds=0.0,
            account=AccountInfoDTO(
                balance=PEAK_EQUITY,
                equity=PEAK_EQUITY,
                margin_level=1500.0,
                margin_free=PEAK_EQUITY,
            ),
        ),
        TimelineStep(
            elapsed_seconds=60.0,
            account=AccountInfoDTO(
                balance=crashed_equity,
                equity=crashed_equity,
                margin_level=180.0,
                margin_free=crashed_equity * Decimal("0.5"),
            ),
        ),
    ]
