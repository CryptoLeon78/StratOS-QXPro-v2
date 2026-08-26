"""PARTE 9.3: autenticacion de WebSocket via token por query param -- el
navegador no puede fijar cabeceras HTTP en el handshake WS. Reutiliza
`auth/jwt.py::decode_token` (ya existe): valida firma/expiry/tipo de token
sin volver a consultar la BBDD (la identidad del JWT ya es de fiar si la
firma valida -- mismo criterio stateless que el resto del sistema de auth,
G5 ASSUMPTIONS: sin revocacion real, ver auth/service.py)."""

import jwt
from fastapi import WebSocket

from core.auth.jwt import TokenPayload, decode_token
from core.config import Settings


async def authenticate_ws(websocket: WebSocket, settings: Settings) -> TokenPayload | None:
    token = websocket.query_params.get("token")
    if token is None:
        return None
    try:
        payload = decode_token(token, settings)
    except jwt.InvalidTokenError:
        return None
    if payload.type != "access":
        return None
    return payload
