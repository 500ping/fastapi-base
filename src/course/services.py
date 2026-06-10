from typing import Optional

from fastapi import status
from sqlalchemy import func, select

from src.common.enums.message_enum import ExceptionMessageEnum
from src.common.exceptions.api_exception import APIException
from src.common.redis.client import distributed_lock
from src.common.services import BaseService
from src.course.constants import MAX_STUDENTS_PER_CLASS, enroll_lock_name
from src.course.dtos.requests.course import CreateClassRequest
from src.course.models import ClassRoom, Enrollment


class CourseService(BaseService):
    # ---- Lookups -----------------------------------------------------------
    async def get_class(self, class_id: int) -> Optional[ClassRoom]:
        return await self.db.get(ClassRoom, class_id)

    async def get_class_or_404(self, class_id: int) -> ClassRoom:
        classroom = await self.get_class(class_id)
        if classroom is None:
            raise APIException(
                status.HTTP_404_NOT_FOUND, ExceptionMessageEnum.CLASS_NOT_FOUND
            )
        return classroom

    async def count_enrollments(self, class_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.class_id == class_id)
        )
        return result.scalar_one()

    async def _is_enrolled(self, class_id: int, student_id: int) -> bool:
        result = await self.db.execute(
            select(Enrollment.id).where(
                Enrollment.class_id == class_id,
                Enrollment.student_id == student_id,
            )
        )
        return result.first() is not None

    # ---- Class creation ----------------------------------------------------
    @BaseService.transaction
    async def create_class(self, owner_id: int, req: CreateClassRequest) -> ClassRoom:
        # The creating user owns the class and is its teacher.
        classroom = ClassRoom(name=req.name, teacher_id=owner_id)
        self.db.add(classroom)
        await self.db.flush()
        return classroom

    # ---- Enrollment --------------------------------------------------------
    async def enroll(self, class_id: int, student_id: int) -> Enrollment:
        """Enroll the given user (a student) into a class under a Redis lock.

        The class existence check is cheap and needs no lock. The capacity
        check is a read-modify-write that must be serialized across
        processes/instances: two concurrent requests could each see the class
        as not-yet-full and both insert, exceeding the cap. The Redis
        distributed lock spans the check, the insert, **and the commit** (which
        happens inside ``_enroll`` while the lock is still held) so the window
        is closed regardless of how many app instances are running.
        """
        await self.get_class_or_404(class_id)
        async with distributed_lock(enroll_lock_name(class_id)):
            return await self._enroll(class_id, student_id)

    @BaseService.transaction
    async def _enroll(self, class_id: int, student_id: int) -> Enrollment:
        # Runs while holding the enrollment lock; this is its own unit of work.
        if await self._is_enrolled(class_id, student_id):
            raise APIException(
                status.HTTP_409_CONFLICT, ExceptionMessageEnum.ALREADY_ENROLLED
            )
        if await self.count_enrollments(class_id) >= MAX_STUDENTS_PER_CLASS:
            raise APIException(
                status.HTTP_409_CONFLICT, ExceptionMessageEnum.CLASS_FULL
            )
        enrollment = Enrollment(class_id=class_id, student_id=student_id)
        self.db.add(enrollment)
        await self.db.flush()
        return enrollment
