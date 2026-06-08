from typing import Any, Dict, List, Optional, TypeVar

from fastapi import status
from pydantic import BaseModel

T = TypeVar("T", List[Any], Dict[str, Any], str, BaseModel)


class Pagination(BaseModel):
    page: int
    size: int
    total: int


class SuccessResponse(BaseModel):
    status_code: int = status.HTTP_200_OK
    msg: str
    data: Optional[T] = None
    pagination: Optional[Pagination] = None
