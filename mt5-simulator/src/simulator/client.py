"""`SimulatedMt5Client`: satisface `Mt5ClientProtocol` (`stratos-mt5-connector`)
estructuralmente, sin heredar de nada -- typing.Protocol se cumple por
forma, no por herencia (asi mt5-connector/src nunca depende de este
paquete; solo sus tests si). Reloj propio (`advance`), determinista, sin
aleatoriedad (son transiciones de estado guionizadas, no una simulacion
estadistica como monte_carlo_maxdd)."""

from dataclasses import dataclass, field
from datetime import datetime

from connector.protocol import AccountInfoDTO, DealDTO, PositionDTO


@dataclass(frozen=True)
class TimelineStep:
    """Estado del terminal a partir de `elapsed_seconds` (segundos de reloj
    simulado desde el arranque del escenario) y hasta el siguiente step.
    `new_deals`: deals que se CIERRAN en este step (se acumulan, no
    reemplazan -- `history_deals_get` los ve todos una vez alcanzado el
    `elapsed_seconds` correspondiente, igual que el terminal real)."""

    elapsed_seconds: float
    account: AccountInfoDTO
    positions: list[PositionDTO] = field(default_factory=list)
    new_deals: list[DealDTO] = field(default_factory=list)


class SimulatedMt5Client:
    def __init__(self, timeline: list[TimelineStep]) -> None:
        if not timeline:
            raise ValueError("timeline no puede estar vacio")
        self._timeline = sorted(timeline, key=lambda s: s.elapsed_seconds)
        self._clock = 0.0

    def advance(self, seconds: float) -> None:
        self._clock += seconds

    def _current_step(self) -> TimelineStep:
        active = [s for s in self._timeline if s.elapsed_seconds <= self._clock]
        return active[-1] if active else self._timeline[0]

    def initialize(self, path: str | None = None) -> bool:
        return True

    def login(self, login: int, password: str, server: str) -> bool:
        return True

    def account_info(self) -> AccountInfoDTO | None:
        return self._current_step().account

    def positions_get(self) -> list[PositionDTO]:
        return list(self._current_step().positions)

    def history_deals_get(self, date_from: datetime, date_to: datetime) -> list[DealDTO]:
        seen: dict[int, DealDTO] = {}
        for step in self._timeline:
            if step.elapsed_seconds > self._clock:
                break
            for deal in step.new_deals:
                if date_from <= deal.time_close <= date_to:
                    seen[deal.ticket] = deal
        return list(seen.values())

    def last_error(self) -> tuple[int, str]:
        return (0, "no error")

    def shutdown(self) -> None:
        return None
