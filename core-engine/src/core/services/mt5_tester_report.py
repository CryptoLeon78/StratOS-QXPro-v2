"""Parser estricto del informe de deals emitido por SQX_vs_MT5.

No es un CSV MT5 genérico: el exportador sellado de este proyecto usa filas
semicolon-separated bajo ``- List of deals -``. La posición de cada campo es
parte de su versión de parser; una variación se retiene antes de entrar en una
matriz operacional.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

PARSER_VERSION = "sqx-vs-mt5-deals-v1"
_SECTION = "- List of deals"


@dataclass(frozen=True)
class TesterClosedDeal:
    closed_at: datetime
    profit: Decimal
    commission: Decimal
    swap: Decimal

    @property
    def net_pnl(self) -> Decimal:
        return self.profit + self.commission + self.swap


def parse_sqx_vs_mt5_closed_deals(payload: bytes) -> list[TesterClosedDeal]:
    """Extrae exclusivamente filas ``out`` con fecha y P&L explícitos."""
    try:
        if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
            text = payload.decode("utf-16")
        else:
            text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("MT5 tester report must be UTF-8 or UTF-16 with BOM") from exc
    if _SECTION not in text:
        raise ValueError("MT5 tester report lacks deals section")
    deals: list[TesterClosedDeal] = []
    in_deals = False
    for raw in text.splitlines():
        if raw.startswith(_SECTION):
            in_deals = True
            continue
        if not in_deals:
            continue
        if raw.startswith("-"):
            break
        if not raw.strip():
            continue
        fields = raw.split(";")
        if len(fields) < 13:
            raise ValueError("MT5 tester deal row has fewer than 13 fields")
        if fields[8].strip().lower() != "out":
            continue
        try:
            deals.append(
                TesterClosedDeal(
                    closed_at=datetime.strptime(fields[4].strip(), "%Y.%m.%d %H:%M:%S"),
                    commission=Decimal(fields[10].strip()),
                    swap=Decimal(fields[11].strip()),
                    profit=Decimal(fields[12].strip()),
                )
            )
        except (ValueError, InvalidOperation) as exc:
            raise ValueError("MT5 tester deal row has invalid close/P&L fields") from exc
    if not deals:
        raise ValueError("MT5 tester report contains no closed deals")
    return deals
