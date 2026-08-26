"""PARTE 9.1: autenticacion de `/ingest/*` via `X-API-Key` contra
`Settings.ingest_api_keys` (PARTE 10.1, ya sembrado en G0). Comparado en
cada request (no cacheado como set): `Settings` esta `lru_cache`d pero un
operador puede rotar `INGEST_API_KEYS` sin recompilar, y parsear una cadena
corta es barato."""

from fastapi import Depends, Header, HTTPException, status

from core.config import Settings, get_settings


async def require_api_key(
    x_api_key: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> str:
    valid_keys = {key.strip() for key in settings.ingest_api_keys.split(",") if key.strip()}
    if x_api_key not in valid_keys:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid X-API-Key")
    return x_api_key
