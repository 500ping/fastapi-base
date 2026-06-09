import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import status
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from src.auth.constants import (
    CLAIM_EXPIRES_AT,
    CLAIM_ISSUED_AT,
    CLAIM_JTI,
    CLAIM_SUBJECT,
    CLAIM_TYPE,
)
from src.auth.enums import TokenType
from src.common.configs.settings import get_settings
from src.common.enums.message_enum import ExceptionMessageEnum
from src.common.exceptions.api_exception import APIException

settings = get_settings()
password_hash = PasswordHash((BcryptHasher(),))


def normalize_email(value: str) -> str:
    """Lowercase and trim email so logins are case-insensitive."""
    return value.strip().lower()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    """Encode a JWT carrying a unique ``jti`` so it can later be revoked."""
    now = datetime.now(timezone.utc)
    payload = {
        CLAIM_SUBJECT: subject,
        CLAIM_JTI: uuid.uuid4().hex,
        CLAIM_TYPE: token_type.value,
        CLAIM_ISSUED_AT: now,
        CLAIM_EXPIRES_AT: now + expires_delta,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise APIException(
            status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.INVALID_TOKEN
        ) from exc
