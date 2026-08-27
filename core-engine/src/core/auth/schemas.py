from typing import Literal

from pydantic import BaseModel


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    # Opcional: revocar tambien el refresh token (30 dias de vida) ademas
    # del access actual (15 min) -- sin el, "logout" solo mataria el token
    # de corta duracion y el usuario seguiria pudiendo pedir uno nuevo.
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
