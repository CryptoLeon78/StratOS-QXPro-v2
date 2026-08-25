-- Ejecutado por el entrypoint oficial de la imagen timescale/timescaledb
-- en la primera inicializacion del volumen (docker-entrypoint-initdb.d).
-- El resto del esquema (hypertables, compresion, continuous aggregates)
-- se gestiona con Alembic desde core-engine (G1), nunca aqui.
CREATE EXTENSION IF NOT EXISTS timescaledb;
