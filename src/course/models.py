from typing import List

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.models import BaseModel


class ClassRoom(BaseModel):
    # "class" is a reserved word, so the model is ClassRoom; the table is "classes".
    # ``teacher_id`` is the user who created/owns the class — there is no separate
    # role; whoever owns a class is its teacher.
    __tablename__ = "classes"

    name: Mapped[str] = mapped_column(String(255))
    teacher_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )

    enrollments: Mapped[List["Enrollment"]] = relationship(back_populates="classroom")


class Enrollment(BaseModel):
    # Association object linking a student (a user) to a class, with its own
    # id/created_at so we record when the student joined.
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_enrollment_class_student"),
    )

    class_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("classes.id"), index=True
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True
    )

    classroom: Mapped["ClassRoom"] = relationship(back_populates="enrollments")
