from typing import Annotated, Optional

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.constants import (
    CLAIM_JTI,
    CLAIM_SUBJECT,
    CLAIM_TYPE,
)
from src.auth.enums import TokenType
from src.auth.models import User
from src.auth.services import AuthService
from src.auth.utils import decode_token
from src.common.configs.settings import get_settings
from src.common.database.session import get_db
from src.common.enums.message_enum import ExceptionMessageEnum
from src.common.exceptions.api_exception import APIException

settings = get_settings()
password_hash = PasswordHash((BcryptHasher(),))
# auto_error=False so a missing/invalid header flows through our APIException
# handler (401 + JSON envelope) instead of Starlette's default 403.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_bearer_token(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> str:
    """Extract the raw bearer token from the Authorization header."""
    if credentials is None:
        raise APIException(
            status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.INVALID_TOKEN
        )
    return credentials.credentials


async def get_current_user(
    token: Annotated[str, Depends(get_bearer_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve the authenticated user from a non-revoked access token."""
    payload = decode_token(token)
    if payload.get(CLAIM_TYPE) != TokenType.ACCESS.value:
        raise APIException(
            status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.INVALID_TOKEN
        )
    service = AuthService(db)
    if await service.is_blacklisted(payload[CLAIM_JTI]):
        raise APIException(
            status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.TOKEN_REVOKED
        )
    user = await service.get_user_by_id(int(payload[CLAIM_SUBJECT]))
    if not user:
        raise APIException(
            status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.USER_NOT_FOUND
        )
    if not user.is_active:
        raise APIException(
            status.HTTP_403_FORBIDDEN, ExceptionMessageEnum.INACTIVE_USER
        )
    return user
