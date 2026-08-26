"""PARTE 9.1: `X-API-Key` contra `Settings.ingest_api_keys` (soporta lista
separada por comas). Unit test directo de la dependency + un test a nivel
ASGI real (primer uso de httpx.ASGITransport en el repo) para probar el
ciclo completo de FastAPI: header ausente -> 422, header invalido -> 401,
header valido -> pasa."""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from core.config import Settings, get_settings
from core.ingest.security import require_api_key


def _settings(ingest_api_keys: str) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        app_database_url="postgresql+asyncpg://u:p@localhost/db",
        app_db_password="x",
        redis_url="redis://localhost/0",
        jwt_secret="x",
        ingest_api_keys=ingest_api_keys,
    )


class TestRequireApiKeyDirect:
    async def test_valid_key_returns_it(self) -> None:
        result = await require_api_key(x_api_key="key1", settings=_settings("key1,key2"))
        assert result == "key1"

    async def test_valid_key_with_surrounding_whitespace_in_config(self) -> None:
        result = await require_api_key(x_api_key="key2", settings=_settings("key1, key2 "))
        assert result == "key2"

    async def test_invalid_key_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(x_api_key="wrong", settings=_settings("key1,key2"))
        assert exc_info.value.status_code == 401

    async def test_empty_key_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(x_api_key="", settings=_settings("key1"))
        assert exc_info.value.status_code == 401


class TestRequireApiKeyAsgi:
    def _build_app(self, ingest_api_keys: str) -> FastAPI:
        app = FastAPI()

        @app.get("/protected")
        async def protected(api_key: str = Depends(require_api_key)) -> dict[str, str]:
            return {"api_key": api_key}

        app.dependency_overrides[get_settings] = lambda: _settings(ingest_api_keys)
        return app

    async def test_missing_header_is_422(self) -> None:
        app = self._build_app("key1")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/protected")
        assert response.status_code == 422

    async def test_wrong_key_is_401(self) -> None:
        app = self._build_app("key1")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/protected", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    async def test_correct_key_is_200(self) -> None:
        app = self._build_app("key1,key2")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/protected", headers={"X-API-Key": "key2"})
        assert response.status_code == 200
        assert response.json() == {"api_key": "key2"}
