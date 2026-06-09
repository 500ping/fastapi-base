from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dtos.requests.auth import SignupRequest
from src.auth.enums import TokenType
from src.auth.models import BlacklistedToken
from src.auth.services import AuthService
from src.auth.utils import create_token, decode_token
from src.common.exceptions.api_exception import APIException


async def test_signup_persists_user_with_id(db_session: AsyncSession) -> None:
    service = AuthService(db_session)

    user = await service.signup(
        SignupRequest(email="new@example.com", password="supersecret")
    )

    assert user.id is not None
    assert user.created_at is not None
    fetched = await service.get_user_by_email("new@example.com")
    assert fetched is not None


async def test_signup_duplicate_raises_and_rolls_back(
    db_session: AsyncSession,
) -> None:
    service = AuthService(db_session)
    await service.signup(SignupRequest(email="dup@example.com", password="supersecret"))

    with pytest.raises(APIException) as exc_info:
        await service.signup(
            SignupRequest(email="dup@example.com", password="supersecret")
        )

    assert exc_info.value.http_status == 409
    count = await db_session.execute(select(func.count()).select_from(BlacklistedToken))
    # No blacklist rows and exactly one user remains.
    assert count.scalar_one() == 0


async def test_logout_blacklists_both_tokens_in_one_transaction(
    db_session: AsyncSession,
) -> None:
    service = AuthService(db_session)
    access = create_token("1", TokenType.ACCESS, timedelta(minutes=5))
    refresh = create_token("1", TokenType.REFRESH, timedelta(days=1))

    await service.logout(access, refresh)

    rows = await db_session.execute(select(BlacklistedToken.token_type))
    types = sorted(row[0] for row in rows.all())
    assert types == [TokenType.ACCESS.value, TokenType.REFRESH.value]


async def test_is_blacklisted_reflects_logout(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    access = create_token("1", TokenType.ACCESS, timedelta(minutes=5))
    refresh = create_token("1", TokenType.REFRESH, timedelta(days=1))

    jti = decode_token(access)["jti"]
    assert await service.is_blacklisted(jti) is False

    await service.logout(access, refresh)

    assert await service.is_blacklisted(jti) is True
