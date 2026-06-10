from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    teacher_id: int
    capacity: int
    enrolled_count: int
    created_at: datetime


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    student_id: int
    created_at: datetime
