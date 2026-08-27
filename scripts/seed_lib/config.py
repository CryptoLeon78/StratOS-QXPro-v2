"""Perfiles de seed (PARTE 13, G8). Solo 2 perfiles reales -- `full`
(cifras literales del enunciado, historia completa 2021-01-04->hoy) y `ci`
(mismos bots/candidatos/lapidas "con nombre" que exige la matriz de
criterios de aceptacion de PARTE 16, historia corta para que sembrar sea
rapido en cada corrida de CI). `small_scale` (PARTE 14/M9) es un producto
real distinto, sin relacion con testing -- no se construye aqui."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

FULL_HISTORY_START = datetime(2021, 1, 4, tzinfo=UTC)
# Cifras literales de PARTE 13 -- el generador se aproxima a estas dentro
# de una tolerancia documentada (ver trades_history.py), no persigue el
# entero exacto: lo que se verifica con assert duro son las propiedades
# agregadas (DD, retorno medio, meses negativos, correlacion, beta).
FULL_TARGET_TRADES = 15_486
FULL_TARGET_BATCHES = 137_296
FULL_TARGET_MAX_DD_PCT = 4.8
FULL_TARGET_MONTHLY_RETURN_PCT = 2.69
FULL_TARGET_NEGATIVE_MONTHS = 14
FULL_TARGET_TOTAL_MONTHS = 66
FULL_TARGET_MEAN_CORRELATION = 0.16
FULL_TARGET_BETA = 0.18

CI_HISTORY_DAYS = 120


@dataclass(frozen=True)
class SeedProfile:
    name: str
    history_start: datetime
    history_end: datetime
    # Solo el perfil full aspira a las cifras literales del enunciado --
    # el resto de la generacion (que bots/candidatos/lapidas existen) es
    # identica entre perfiles, ver bots_production.py/bots_pipeline.py/
    # graveyard.py.
    match_literal_totals: bool


def full_profile(now: datetime) -> SeedProfile:
    return SeedProfile(
        name="full", history_start=FULL_HISTORY_START, history_end=now, match_literal_totals=True
    )


def ci_profile(now: datetime) -> SeedProfile:
    return SeedProfile(
        name="ci",
        history_start=now - timedelta(days=CI_HISTORY_DAYS),
        history_end=now,
        match_literal_totals=False,
    )


def profile_for(name: str, now: datetime | None = None) -> SeedProfile:
    now = now or datetime.now(UTC)
    if name == "full":
        return full_profile(now)
    if name == "ci":
        return ci_profile(now)
    raise ValueError(f"perfil de seed desconocido: {name!r} (usa 'full' o 'ci')")
