import orjson
from fastapi import status
from fastapi.exceptions import RequestValidationError

from src.common.enums.message_enum import ExceptionMessageEnum
from src.common.exceptions.api_exception import APIException
from src.common.handlers.exception_handler import (
    exception_handler,
    validation_exception_handler,
)


async def test_api_exception_uses_its_status_and_message() -> None:
    exc = APIException(
        status.HTTP_409_CONFLICT, ExceptionMessageEnum.EMAIL_ALREADY_REGISTERED
    )

    resp = await exception_handler(None, exc)
    body = orjson.loads(resp.body)

    assert resp.status_code == status.HTTP_409_CONFLICT
    assert body == {
        "status_code": status.HTTP_409_CONFLICT,
        "msg": ExceptionMessageEnum.EMAIL_ALREADY_REGISTERED,
    }


async def test_unexpected_exception_becomes_500() -> None:
    resp = await exception_handler(None, ValueError("boom"))
    body = orjson.loads(resp.body)

    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert body["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_validation_handler_shapes_details() -> None:
    exc = RequestValidationError(
        [
            {
                "loc": ("body", "email"),
                "msg": "value is not a valid email address",
                "type": "value_error",
            }
        ]
    )

    resp = await validation_exception_handler(None, exc)
    body = orjson.loads(resp.body)

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert body["msg"] == "Validation Error"
    assert body["details"][0]["field"] == "body -> email"
    assert body["details"][0]["type"] == "value_error"
