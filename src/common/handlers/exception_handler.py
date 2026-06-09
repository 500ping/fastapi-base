from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.common.exceptions.api_exception import APIException


async def exception_handler(_: Request, exc: Exception | APIException) -> JSONResponse:
    """
    Custom exception handler for the application
    """
    if isinstance(exc, APIException):
        return JSONResponse(
            status_code=exc.http_status,
            content={"status_code": exc.http_status, "msg": exc.message},
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "msg": "Internal Server Error",
        },
    )


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI/Pydantic validation errors
    """
    # Extract validation error details
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_msg = error["msg"]
        error_type = error["type"]
        errors.append({"field": field_path, "message": error_msg, "type": error_type})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "msg": "Validation Error",
            "details": errors,
        },
    )
