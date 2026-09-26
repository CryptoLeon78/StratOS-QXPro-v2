"""El pool de conexiones se dimensiona por despliegue, no por el default de la libreria.

El stack operacional recibe telemetria continua de dos cuentas reales por tunel
mientras el operador usa la UI. Con el default implicito de SQLAlchemy (5 + 10)
la ingesta agota las 15 conexiones y **el login deja de responder**: cada
peticion espera 30 s y devuelve 500. El tamano del pool es un parametro de
despliegue (P11), no algo que se hereda sin declararlo.
"""

from __future__ import annotations

from core.db.base import make_engine

URL = "postgresql+asyncpg://u:p@localhost:5432/d"


def test_el_engine_declara_el_tamano_del_pool() -> None:
    engine = make_engine(URL, pool_size=25, max_overflow=15)

    pool = engine.pool
    assert pool.size() == 25
    assert pool._max_overflow == 15


def test_el_pool_por_defecto_supera_al_implicito_de_sqlalchemy() -> None:
    """Sin argumentos explicitos el default propio debe ser mayor que 5 + 10."""
    engine = make_engine(URL)

    assert engine.pool.size() + engine.pool._max_overflow > 15
