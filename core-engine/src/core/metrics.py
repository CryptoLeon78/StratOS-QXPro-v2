"""Prometheus (PARTE 12 G5: "Prometheus" listado sin lista cerrada de
metricas -- PARTE 9/10 no fija ninguna salvo `telegram_failures_total`,
citada literal en 9.4, ya en notifications/telegram.py). Set minimo
razonable, documentado aqui en vez de inventado ad-hoc por endpoint:
peticiones HTTP, duracion de jobs ARQ, conexiones WS activas.

`GET /metrics` sin autenticacion -- coherente con un scrape directo de
Prometheus (`infra/prometheus/prometheus.yml`) sin credenciales
(ASSUMPTIONS G5, no es un agujero de seguridad sin revisar)."""

import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", "Peticiones HTTP recibidas", ["method", "path_template", "status"]
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds", "Duracion de peticiones HTTP", ["method", "path_template"]
)
ARQ_JOB_DURATION_SECONDS = Histogram(
    "arq_job_duration_seconds", "Duracion de jobs ARQ", ["job_name"]
)
ARQ_JOB_FAILURES_TOTAL = Counter(
    "arq_job_failures_total", "Jobs ARQ que lanzaron una excepcion", ["job_name"]
)
WS_CONNECTIONS_ACTIVE = Gauge("ws_connections_active", "Conexiones WebSocket activas", ["channel"])

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        path_template = route.path if route is not None else request.url.path

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method, path_template=path_template, status=response.status_code
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method, path_template=path_template
        ).observe(duration)
        return response
