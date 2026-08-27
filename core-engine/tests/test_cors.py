"""G6: el frontend (Vite dev server, http://localhost:5173) llama a
core-engine directo, sin api-gateway de por medio (ASSUMPTIONS G6-00) --
sin CORSMiddleware el navegador bloquearia toda peticion cross-origin."""

from fastapi.testclient import TestClient

from core.main import app


def test_allowed_origin_gets_cors_headers_on_preflight() -> None:
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_disallowed_origin_gets_no_cors_headers_on_preflight() -> None:
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_actual_response_carries_cors_header() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_playwright_harness_origin_5175_also_allowed() -> None:
    """G8: bug real encontrado -- sin :5175 en la lista, el harness
    Playwright (`frontend/playwright.config.ts`, puerto deliberadamente
    distinto de :5173) fallaba en TODA peticion por CORS, enmascarado en
    la UI como "credenciales incorrectas". Ver ASSUMPTIONS G8."""
    client = TestClient(app)
    response = client.get("/health", headers={"Origin": "http://localhost:5175"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5175"
