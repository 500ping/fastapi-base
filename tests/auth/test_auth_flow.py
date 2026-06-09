from httpx import AsyncClient

SIGNUP = "/api/v1/auth/signup"
SIGNIN = "/api/v1/auth/signin"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"

CREDS = {"email": "user@example.com", "password": "supersecret"}


async def _signup(client: AsyncClient, **over) -> None:
    await client.post(SIGNUP, json={**CREDS, **over})


async def _signin(client: AsyncClient, **over) -> dict:
    resp = await client.post(SIGNIN, json={**CREDS, **over})
    return resp.json()["data"]


async def test_signup_success(client: AsyncClient) -> None:
    resp = await client.post(SIGNUP, json=CREDS)

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["email"] == "user@example.com"
    assert data["id"] is not None
    assert data["is_active"] is True


async def test_signup_duplicate_returns_409(client: AsyncClient) -> None:
    await _signup(client)

    resp = await client.post(SIGNUP, json=CREDS)

    assert resp.status_code == 409
    assert resp.json()["msg"] == "Email already registered"


async def test_signup_invalid_payload_returns_422(client: AsyncClient) -> None:
    resp = await client.post(SIGNUP, json={"email": "nope", "password": "x"})

    assert resp.status_code == 422
    body = resp.json()
    assert body["msg"] == "Validation Error"
    assert body["details"]


async def test_signin_success_returns_tokens(client: AsyncClient) -> None:
    await _signup(client)

    data = await _signin(client)

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


async def test_signin_wrong_password_returns_401(client: AsyncClient) -> None:
    await _signup(client)

    resp = await client.post(SIGNIN, json={**CREDS, "password": "wrong"})

    assert resp.status_code == 401
    assert resp.json()["msg"] == "Invalid email or password"


async def test_signin_unknown_user_returns_401(client: AsyncClient) -> None:
    resp = await client.post(SIGNIN, json=CREDS)

    assert resp.status_code == 401


async def test_email_login_is_case_insensitive(client: AsyncClient) -> None:
    await _signup(client, email="user@example.com")

    resp = await client.post(
        SIGNIN, json={"email": "  USER@Example.COM  ", "password": "supersecret"}
    )

    assert resp.status_code == 200


async def test_signup_duplicate_different_case_returns_409(
    client: AsyncClient,
) -> None:
    await _signup(client, email="user@example.com")

    resp = await client.post(
        SIGNUP, json={"email": "USER@EXAMPLE.COM", "password": "supersecret"}
    )

    assert resp.status_code == 409


async def test_refresh_returns_new_tokens(client: AsyncClient) -> None:
    await _signup(client)
    tokens = await _signin(client)

    resp = await client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})

    assert resp.status_code == 200
    assert resp.json()["data"]["access_token"]


async def test_refresh_with_access_token_returns_401(client: AsyncClient) -> None:
    await _signup(client)
    tokens = await _signin(client)

    # Passing an access token where a refresh token is expected.
    resp = await client.post(REFRESH, json={"refresh_token": tokens["access_token"]})

    assert resp.status_code == 401


async def test_logout_requires_authentication(client: AsyncClient) -> None:
    resp = await client.post(LOGOUT, json={"refresh_token": "whatever"})

    assert resp.status_code == 401


async def test_logout_revokes_both_tokens(client: AsyncClient) -> None:
    await _signup(client)
    tokens = await _signin(client)
    auth_header = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout = await client.post(
        LOGOUT, headers=auth_header, json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout.status_code == 200

    # Access token is now revoked.
    reuse = await client.post(
        LOGOUT, headers=auth_header, json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse.status_code == 401
    assert reuse.json()["msg"] == "Token has been revoked"

    # Refresh token is now revoked too.
    refresh = await client.post(
        REFRESH, json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401
    assert refresh.json()["msg"] == "Token has been revoked"
