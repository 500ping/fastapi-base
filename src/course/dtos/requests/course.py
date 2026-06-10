from pydantic import BaseModel, Field


class CreateClassRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Algorithms 101"])
