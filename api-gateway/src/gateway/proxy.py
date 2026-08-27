"""Proxy transparente hacia core-engine (G9, PARTE 3/12): reenvia cualquier
metodo/ruta tal cual, sin re-declarar los routers de core-engine -- cero
logica de dominio, cumple la regla arquitectonica "gateway sin dominio".
El gateway nunca valida el JWT: solo reenvia el header Authorization
intacto, core-engine sigue siendo la unica fuente de verdad de auth."""

import httpx

# Hop-by-hop (RFC 7230 6.1) + Host: el cliente httpx los recalcula el mismo
# hacia el upstream, reenviarlos tal cual rompe la conexion o duplica datos.
_EXCLUDED_REQUEST_HEADERS = {
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


async def forward_request(
    *,
    method: str,
    path: str,
    query: str,
    headers: dict[str, str],
    body: bytes,
    client: httpx.AsyncClient,
    upstream_base_url: str,
) -> httpx.Response:
    url = f"{upstream_base_url}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{query}"

    forwarded_headers = {
        key: value for key, value in headers.items() if key.lower() not in _EXCLUDED_REQUEST_HEADERS
    }

    return await client.request(
        method,
        url,
        headers=forwarded_headers,
        content=body,
        follow_redirects=False,
    )
