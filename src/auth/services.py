from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import status
from sqlalchemy import select

from src.auth.constants import (
    CLAIM_EXPIRES_AT,
    CLAIM_JTI,
    CLAIM_SUBJECT,
    CLAIM_TYPE,
)
from src.auth.dtos.requests.auth import RefreshRequest, SigninRequest, SignupRequest
from src.auth.dtos.responses.auth import TokenResponse
from src.auth.enums import TokenType
from src.auth.models import BlacklistedToken, User
from src.auth.utils import create_token, decode_token, hash_password, verify_password
from src.common.configs.settings import get_settings
from src.common.enums.message_enum import ExceptionMessageEnum
from src.common.exceptions.api_exception import APIException
from src.common.services import BaseService

settings = get_settings()


class AuthService(BaseService):
    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        return await self.db.get(User, user_id)

    async def is_blacklisted(self, jti: str) -> bool:
        result = await self.db.execute(
            select(BlacklistedToken.id).where(BlacklistedToken.jti == jti)
        )
        return result.first() is not None

    @BaseService.transaction
    async def signup(self, req: SignupRequest) -> User:
        if await self.get_user_by_email(req.email):
            raise APIException(
                status.HTTP_409_CONFLICT,
                ExceptionMessageEnum.EMAIL_ALREADY_REGISTERED,
            )
        user = User(email=req.email, hashed_password=hash_password(req.password))
        self.db.add(user)
        # Flush (not commit) so id/created_at are populated within the
        # transaction; the @transaction decorator owns the final commit.
        await self.db.flush()
        return user

    async def signin(self, req: SigninRequest) -> TokenResponse:
        user = await self.get_user_by_email(req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            raise APIException(
                status.HTTP_401_UNAUTHORIZED,
                ExceptionMessageEnum.INVALID_CREDENTIALS,
            )
        return self.create_tokens(user)

    def create_tokens(self, user: User) -> TokenResponse:
        subject = str(user.id)
        access_token = create_token(
            subject,
            TokenType.ACCESS,
            timedelta(minutes=settings.access_token_expire_minutes),
        )
        refresh_token = create_token(
            subject,
            TokenType.REFRESH,
            timedelta(days=settings.refresh_token_expire_days),
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, req: RefreshRequest) -> TokenResponse:
        payload = decode_token(req.refresh_token)
        if payload.get(CLAIM_TYPE) != TokenType.REFRESH.value:
            raise APIException(
                status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.INVALID_TOKEN
            )
        if await self.is_blacklisted(payload[CLAIM_JTI]):
            raise APIException(
                status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.TOKEN_REVOKED
            )
        user = await self.get_user_by_id(int(payload[CLAIM_SUBJECT]))
        if not user:
            raise APIException(
                status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.USER_NOT_FOUND
            )
        return self.create_tokens(user)

    @BaseService.transaction
    async def logout(self, access_token: str, refresh_token: str) -> None:
        for token in (access_token, refresh_token):
            await self._blacklist(token)

    async def _blacklist(self, token: str) -> None:
        payload = decode_token(token)
        jti = payload[CLAIM_JTI]
        if await self.is_blacklisted(jti):
            return
        self.db.add(
            BlacklistedToken(
                jti=jti,
                token_type=payload.get(CLAIM_TYPE, ""),
                expires_at=datetime.fromtimestamp(
                    payload[CLAIM_EXPIRES_AT], tz=timezone.utc
                ),
            )
        )
