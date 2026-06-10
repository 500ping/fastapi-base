from typing import Optional

from pydantic import BaseModel, Field

from src.common.dtos.requests.pagination import PaginationParams
from src.course.enums import ClassRelation


class CreateClassRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Algorithms 101"])


class ListClassesParams(PaginationParams):
    relation: Optional[ClassRelation] = Field(
        default=None,
        description=(
            "Scope to the current user: 'owner' for classes they teach, "
            "'joiner' for classes they joined. Omit for all classes."
        ),
    )
