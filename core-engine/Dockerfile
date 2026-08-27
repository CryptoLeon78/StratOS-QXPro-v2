# Contexto de build = raiz del repo (ver docker-compose.yml: "context: .,
# dockerfile: core-engine/Dockerfile") -- core-engine depende de
# stratos-ingest-seal, un paquete LOCAL del monorepo (shared-ingest-seal/,
# no esta en ningun indice publico), asi que el contexto tiene que
# alcanzar a su hermano fuera de core-engine/. Hallazgo real de G8
# (criterio 17, primera vez que se construye esta imagen): con el
# contexto limitado a ./core-engine, `pip install .` intentaba resolver
# stratos-ingest-seal contra PyPI y fallaba.
FROM python:3.12-slim AS builder
# statsmodels no publica wheel para esta combinacion exacta de plataforma/
# version y compila desde el sdist (Meson) -- python:3.12-slim no trae
# compilador. Segundo hallazgo real de G8 en el mismo intento de build.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY shared-ingest-seal ./shared-ingest-seal
COPY core-engine/pyproject.toml ./core-engine/pyproject.toml
COPY core-engine/src ./core-engine/src
# Los 2 paquetes locales en UNA sola invocacion de pip -- instalados por
# separado, la resolucion de core-engine (2ª llamada) no ve el paquete
# que la 1ª acaba de instalar bajo --prefix=/install (no esta en el path
# de busqueda de ESE pip) y sale a buscar stratos-ingest-seal en PyPI,
# donde no existe (tercer hallazgo real de G8 en el mismo build).
RUN pip install --no-cache-dir --prefix=/install ./shared-ingest-seal ./core-engine

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY core-engine/src ./src
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000"]
