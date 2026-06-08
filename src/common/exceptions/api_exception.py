from fastapi import status

from src.common.enums.message_enum import ExceptionMessageEnum


class APIException(Exception):
    def __init__(
        self,
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=ExceptionMessageEnum.DEFAULT,
    ):
        self.http_status = http_status
        self.message = message

        super().__init__()
