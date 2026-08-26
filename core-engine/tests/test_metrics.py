"""GET /metrics no requiere auth -- prueba end-to-end contra core.main.app
sin dependency_overrides de get_current_user (mismo criterio que
tests/ws/test_router.py::TestWsAuth para verificar el flujo real, no un
mock)."""

from httpx import ASGITransport, AsyncClient

from core.main import app


async def test_metrics_is_public_and_exposes_prometheus_text_format() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


async def test_a_request_is_recorded_in_http_requests_total() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/health")
        response = await client.get("/metrics")
    body = response.text
    assert 'http_requests_total{method="GET",path_template="/health",status="200"}' in body
