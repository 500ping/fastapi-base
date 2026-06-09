"""OpenAPI response examples for the auth routes.

Kept out of ``routers.py`` so the route definitions stay readable. Error
messages are sourced from :class:`ExceptionMessageEnum` so the docs stay in
sync with what the handlers actually return.
"""

from fastapi import status

from src.common.enums.message_enum import ExceptionMessageEnum

_ACCESS_TOKEN_EXAMPLE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyJ9"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)
_REFRESH_TOKEN_EXAMPLE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2gifQ"
    ".h3fAo0vQ1m2bq9rXk7Zt6yJ8sN0pLwQeR4uT5vW6xY"
)

_TOKEN_DATA_EXAMPLE = {
    "access_token": _ACCESS_TOKEN_EXAMPLE,
    "refresh_token": _REFRESH_TOKEN_EXAMPLE,
    "token_type": "bearer",
}


def _content(example=None, examples=None) -> dict:
    media: dict = {}
    if example is not None:
        media["example"] = example
    if examples is not None:
        media["examples"] = examples
    return {"application/json": media}


def _response(description: str, *, example=None, examples=None) -> dict:
    return {"description": description, "content": _content(example, examples)}


def _error(status_code: int, message: ExceptionMessageEnum) -> dict:
    return {"status_code": status_code, "msg": str(message)}


# Shared 422 example produced by ``validation_exception_handler``.
VALIDATION_RESPONSE = _response(
    "Request validation failed",
    example={
        "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "msg": "Validation Error",
        "details": [
            {
                "field": "body -> email",
                "message": (
                    "value is not a valid email address: "
                    "An email address must have an @-sign."
                ),
                "type": "value_error",
            },
            {
                "field": "body -> password",
                "message": "String should have at least 8 characters",
                "type": "string_too_short",
            },
        ],
    },
)


SIGNUP_RESPONSES = {
    status.HTTP_201_CREATED: _response(
        "User created successfully",
        example={
            "status_code": status.HTTP_201_CREATED,
            "msg": "User created successfully",
            "data": {
                "id": 1,
                "email": "user@example.com",
                "is_active": True,
                "created_at": "2026-06-09T07:24:01.986311Z",
            },
        },
    ),
    status.HTTP_409_CONFLICT: _response(
        "Email already registered",
        example=_error(
            status.HTTP_409_CONFLICT,
            ExceptionMessageEnum.EMAIL_ALREADY_REGISTERED,
        ),
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: VALIDATION_RESPONSE,
}


SIGNIN_RESPONSES = {
    status.HTTP_200_OK: _response(
        "Signed in successfully",
        example={
            "status_code": status.HTTP_200_OK,
            "msg": "Signed in successfully",
            "data": _TOKEN_DATA_EXAMPLE,
        },
    ),
    status.HTTP_401_UNAUTHORIZED: _response(
        "Invalid credentials",
        example=_error(
            status.HTTP_401_UNAUTHORIZED,
            ExceptionMessageEnum.INVALID_CREDENTIALS,
        ),
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: VALIDATION_RESPONSE,
}


REFRESH_RESPONSES = {
    status.HTTP_200_OK: _response(
        "Token refreshed successfully",
        example={
            "status_code": status.HTTP_200_OK,
            "msg": "Token refreshed successfully",
            "data": _TOKEN_DATA_EXAMPLE,
        },
    ),
    status.HTTP_401_UNAUTHORIZED: _response(
        "Invalid or revoked refresh token",
        examples={
            "invalid_token": {
                "summary": "Malformed, expired, or non-refresh token",
                "value": _error(
                    status.HTTP_401_UNAUTHORIZED,
                    ExceptionMessageEnum.INVALID_TOKEN,
                ),
            },
            "token_revoked": {
                "summary": "Refresh token was revoked at logout",
                "value": _error(
                    status.HTTP_401_UNAUTHORIZED,
                    ExceptionMessageEnum.TOKEN_REVOKED,
                ),
            },
            "user_not_found": {
                "summary": "User no longer exists",
                "value": _error(
                    status.HTTP_401_UNAUTHORIZED,
                    ExceptionMessageEnum.USER_NOT_FOUND,
                ),
            },
        },
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: VALIDATION_RESPONSE,
}


LOGOUT_RESPONSES = {
    status.HTTP_200_OK: _response(
        "Logged out successfully",
        example={
            "status_code": status.HTTP_200_OK,
            "msg": "Logged out successfully",
        },
    ),
    status.HTTP_401_UNAUTHORIZED: _response(
        "Missing, invalid, or revoked access token",
        examples={
            "invalid_token": {
                "summary": "Missing or malformed access token",
                "value": _error(
                    status.HTTP_401_UNAUTHORIZED,
                    ExceptionMessageEnum.INVALID_TOKEN,
                ),
            },
            "token_revoked": {
                "summary": "Access token was already revoked",
                "value": _error(
                    status.HTTP_401_UNAUTHORIZED,
                    ExceptionMessageEnum.TOKEN_REVOKED,
                ),
            },
            "user_not_found": {
                "summary": "User no longer exists",
                "value": _error(
                    status.HTTP_401_UNAUTHORIZED,
                    ExceptionMessageEnum.USER_NOT_FOUND,
                ),
            },
        },
    ),
    status.HTTP_403_FORBIDDEN: _response(
        "Inactive user",
        example=_error(
            status.HTTP_403_FORBIDDEN,
            ExceptionMessageEnum.INACTIVE_USER,
        ),
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: VALIDATION_RESPONSE,
}
