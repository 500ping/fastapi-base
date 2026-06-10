from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


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


class StudentResponse(BaseModel):
    """A student (user) enrolled in a class, with when they joined."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    enrolled_at: datetime
