"""OpenAPI response examples for the course routes.

Kept out of ``routers.py`` so the route definitions stay readable. Error
messages are sourced from :class:`ExceptionMessageEnum` so the docs stay in
sync with what the handlers actually return.
"""

from fastapi import status

from src.common.enums.message_enum import ExceptionMessageEnum
from src.course.constants import MAX_STUDENTS_PER_CLASS


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


VALIDATION_RESPONSE = _response(
    "Request validation failed",
    example={
        "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "msg": "Validation Error",
        "details": [
            {
                "field": "body -> name",
                "message": "String should have at least 1 character",
                "type": "string_too_short",
            }
        ],
    },
)

# All course routes require a valid access token (see get_current_user).
UNAUTHORIZED_RESPONSE = _response(
    "Missing, invalid, or revoked access token",
    example=_error(status.HTTP_401_UNAUTHORIZED, ExceptionMessageEnum.INVALID_TOKEN),
)


_CLASS_DATA_EXAMPLE = {
    "id": 1,
    "name": "Algorithms 101",
    "teacher_id": 1,
    "capacity": MAX_STUDENTS_PER_CLASS,
    "enrolled_count": 0,
    "created_at": "2026-06-10T07:24:01.986311Z",
}


CREATE_CLASS_RESPONSES = {
    status.HTTP_201_CREATED: _response(
        "Class created successfully",
        example={
            "status_code": status.HTTP_201_CREATED,
            "msg": "Class created successfully",
            "data": _CLASS_DATA_EXAMPLE,
        },
    ),
    status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
    status.HTTP_422_UNPROCESSABLE_CONTENT: VALIDATION_RESPONSE,
}


GET_CLASS_RESPONSES = {
    status.HTTP_200_OK: _response(
        "Class retrieved successfully",
        example={
            "status_code": status.HTTP_200_OK,
            "msg": "Class retrieved successfully",
            "data": {**_CLASS_DATA_EXAMPLE, "enrolled_count": 12},
        },
    ),
    status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
    status.HTTP_404_NOT_FOUND: _response(
        "Class not found",
        example=_error(status.HTTP_404_NOT_FOUND, ExceptionMessageEnum.CLASS_NOT_FOUND),
    ),
}


ENROLL_RESPONSES = {
    status.HTTP_201_CREATED: _response(
        "Enrolled successfully",
        example={
            "status_code": status.HTTP_201_CREATED,
            "msg": "Enrolled successfully",
            "data": {
                "id": 1,
                "class_id": 1,
                "student_id": 1,
                "created_at": "2026-06-10T07:24:01.986311Z",
            },
        },
    ),
    status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_RESPONSE,
    status.HTTP_404_NOT_FOUND: _response(
        "Class not found",
        example=_error(status.HTTP_404_NOT_FOUND, ExceptionMessageEnum.CLASS_NOT_FOUND),
    ),
    status.HTTP_409_CONFLICT: _response(
        "Cannot enroll in the class",
        examples={
            "already_enrolled": {
                "summary": "You are already in the class",
                "value": _error(
                    status.HTTP_409_CONFLICT, ExceptionMessageEnum.ALREADY_ENROLLED
                ),
            },
            "class_full": {
                "summary": "Class is at capacity",
                "value": _error(
                    status.HTTP_409_CONFLICT, ExceptionMessageEnum.CLASS_FULL
                ),
            },
        },
    ),
    status.HTTP_503_SERVICE_UNAVAILABLE: _response(
        "Could not acquire the enrollment lock",
        example=_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            ExceptionMessageEnum.LOCK_UNAVAILABLE,
        ),
    ),
}
