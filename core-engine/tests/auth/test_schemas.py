import pytest
from pydantic import ValidationError

from core.auth.schemas import RefreshRequest, TokenResponse


def test_token_response_defaults_token_type_bearer() -> None:
    response = TokenResponse(access_token="a", refresh_token="r", expires_in=900)
    assert response.token_type == "bearer"


def test_refresh_request_requires_refresh_token() -> None:
    with pytest.raises(ValidationError):
        RefreshRequest()  # type: ignore[call-arg]
