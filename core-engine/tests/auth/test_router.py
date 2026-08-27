from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from tests.factories import TEST_USER_PASSWORD, UserFactory


async def _persist_user(db_connection: AsyncConnection) -> object:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    user = UserFactory()
    session.add(user)
    await session.commit()
    return user


async def test_login_with_correct_credentials_returns_token_pair(
    auth_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    user = await _persist_user(db_connection)
    response = await auth_client.post(
        "/auth/token",
        data={"username": user.email, "password": TEST_USER_PASSWORD},  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_with_wrong_password_returns_401(
    auth_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    user = await _persist_user(db_connection)
    response = await auth_client.post(
        "/auth/token",
        data={"username": user.email, "password": "wrong"},  # type: ignore[attr-defined]
    )
    assert response.status_code == 401


async def test_login_with_unknown_email_returns_401(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/auth/token", data={"username": "nobody@stratos.local", "password": "whatever"}
    )
    assert response.status_code == 401


async def test_refresh_with_valid_refresh_token_rotates_pair(
    auth_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    user = await _persist_user(db_connection)
    login = await auth_client.post(
        "/auth/token",
        data={"username": user.email, "password": TEST_USER_PASSWORD},  # type: ignore[attr-defined]
    )
    original_refresh = login.json()["refresh_token"]
    response = await auth_client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_refresh_with_an_access_token_returns_401(
    auth_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    user = await _persist_user(db_connection)
    login = await auth_client.post(
        "/auth/token",
        data={"username": user.email, "password": TEST_USER_PASSWORD},  # type: ignore[attr-defined]
    )
    access_token = login.json()["access_token"]
    response = await auth_client.post("/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


async def test_refresh_with_garbage_token_returns_401(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert response.status_code == 401


async def test_reusing_a_rotated_refresh_token_returns_401(
    auth_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    user = await _persist_user(db_connection)
    login = await auth_client.post(
        "/auth/token",
        data={"username": user.email, "password": TEST_USER_PASSWORD},  # type: ignore[attr-defined]
    )
    original_refresh = login.json()["refresh_token"]
    first = await auth_client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert first.status_code == 200

    second = await auth_client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert second.status_code == 401


async def test_logout_revokes_the_current_access_token(
    auth_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    user = await _persist_user(db_connection)
    login = await auth_client.post(
        "/auth/token",
        data={"username": user.email, "password": TEST_USER_PASSWORD},  # type: ignore[attr-defined]
    )
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    before = await auth_client.get("/api/v1/header/summary", headers=headers)
    assert before.status_code == 200

    logout_response = await auth_client.post("/auth/logout", json={}, headers=headers)
    assert logout_response.status_code == 204

    after = await auth_client.get("/api/v1/header/summary", headers=headers)
    assert after.status_code == 401


async def test_logout_also_revokes_the_refresh_token_when_provided(
    auth_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    user = await _persist_user(db_connection)
    login = await auth_client.post(
        "/auth/token",
        data={"username": user.email, "password": TEST_USER_PASSWORD},  # type: ignore[attr-defined]
    )
    access_token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    logout_response = await auth_client.post(
        "/auth/logout", json={"refresh_token": refresh_token}, headers=headers
    )
    assert logout_response.status_code == 204

    refresh_response = await auth_client.post(
        "/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401


async def test_logout_without_a_valid_access_token_returns_401(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/auth/logout", json={}, headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401
