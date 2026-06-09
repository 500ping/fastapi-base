from datetime import timedelta

import pytest

from src.auth.constants import CLAIM_JTI, CLAIM_SUBJECT, CLAIM_TYPE
from src.auth.enums import TokenType
from src.auth.utils import (
    create_token,
    decode_token,
    hash_password,
    normalize_email,
    verify_password,
)
from src.common.exceptions.api_exception import APIException


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("supersecret")

    assert hashed != "supersecret"
    assert verify_password("supersecret", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("USER@Example.COM", "user@example.com"),
        ("  user@example.com  ", "user@example.com"),
        ("MixedCase@Domain.io", "mixedcase@domain.io"),
    ],
)
def test_normalize_email(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected


def test_create_and_decode_token() -> None:
    token = create_token("42", TokenType.ACCESS, timedelta(minutes=5))

    payload = decode_token(token)

    assert payload[CLAIM_SUBJECT] == "42"
    assert payload[CLAIM_TYPE] == TokenType.ACCESS.value
    assert payload[CLAIM_JTI]


def test_decode_invalid_token_raises_api_exception() -> None:
    with pytest.raises(APIException) as exc_info:
        decode_token("not-a-jwt")

    assert exc_info.value.http_status == 401


def test_decode_expired_token_raises() -> None:
    expired = create_token("1", TokenType.ACCESS, timedelta(seconds=-1))

    with pytest.raises(APIException):
        decode_token(expired)
