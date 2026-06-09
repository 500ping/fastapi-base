from typing import Generic, Optional, TypeVar

from fastapi import status
from pydantic import BaseModel

T = TypeVar("T")


class Pagination(BaseModel):
    page: int
    size: int
    total: int


class SuccessResponse(BaseModel, Generic[T]):
    status_code: int = status.HTTP_200_OK
    msg: str
    data: Optional[T] = None
    pagination: Optional[Pagination] = None
