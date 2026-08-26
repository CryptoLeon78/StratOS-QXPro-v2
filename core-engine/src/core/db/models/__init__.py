"""Importa todos los modulos de modelos para que Base.metadata los vea
completos (imprescindible para que Alembic autogenere sobre el esquema
entero, PARTE 5.2)."""

from core.db.models import accounts, decisions, market  # noqa: F401
