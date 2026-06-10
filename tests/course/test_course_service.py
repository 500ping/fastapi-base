import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import src.course.services as course_services
from src.auth.models import User
from src.common.enums.message_enum import ExceptionMessageEnum
from src.common.exceptions.api_exception import APIException
from src.course.constants import MAX_STUDENTS_PER_CLASS
from src.course.dtos.requests.course import CreateClassRequest
from src.course.services import CourseService


async def _make_user(db_session: AsyncSession, email: str) -> int:
    user = User(email=email, hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    return user.id


async def test_create_class_sets_owner(db_session: AsyncSession) -> None:
    service = CourseService(db_session)
    owner_id = await _make_user(db_session, "teacher@example.com")

    classroom = await service.create_class(
        owner_id, CreateClassRequest(name="Algorithms")
    )

    assert classroom.teacher_id == owner_id


async def test_enroll_then_count(db_session: AsyncSession, redis_client) -> None:
    service = CourseService(db_session)
    owner_id = await _make_user(db_session, "teacher@example.com")
    student_id = await _make_user(db_session, "student@example.com")
    classroom = await service.create_class(
        owner_id, CreateClassRequest(name="Algorithms")
    )

    await service.enroll(classroom.id, student_id)

    assert await service.count_enrollments(classroom.id) == 1


async def test_enroll_missing_class_raises_404(
    db_session: AsyncSession, redis_client
) -> None:
    service = CourseService(db_session)
    student_id = await _make_user(db_session, "student@example.com")

    with pytest.raises(APIException) as exc:
        await service.enroll(999, student_id)

    assert exc.value.http_status == 404


async def test_enroll_beyond_capacity_returns_409(
    db_session: AsyncSession, redis_client
) -> None:
    service = CourseService(db_session)
    owner_id = await _make_user(db_session, "teacher@example.com")
    classroom = await service.create_class(
        owner_id, CreateClassRequest(name="Algorithms")
    )
    # Hold the id as a plain int: the rejected enrollment below rolls back the
    # transaction, which expires ORM attributes on `classroom`.
    class_id = classroom.id

    # Fill the class to its full capacity (40 students).
    for i in range(MAX_STUDENTS_PER_CLASS):
        student_id = await _make_user(db_session, f"s{i}@example.com")
        await service.enroll(class_id, student_id)
    assert await service.count_enrollments(class_id) == MAX_STUDENTS_PER_CLASS

    # The next student exceeds the cap and is rejected.
    overflow_id = await _make_user(db_session, "overflow@example.com")
    with pytest.raises(APIException) as exc:
        await service.enroll(class_id, overflow_id)

    assert exc.value.http_status == 409
    assert exc.value.message == ExceptionMessageEnum.CLASS_FULL
    # Still exactly at capacity — the overflow enrollment was rolled back.
    assert await service.count_enrollments(class_id) == MAX_STUDENTS_PER_CLASS


async def test_capacity_enforced_under_concurrency(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    redis_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent enrollments must never exceed the cap.

    The Redis distributed lock serializes the read-modify-write so that, even
    with many simultaneous requests, exactly ``cap`` students get a seat.
    """
    cap = 3
    over_subscribe = 5
    monkeypatch.setattr(course_services, "MAX_STUDENTS_PER_CLASS", cap)

    setup = CourseService(db_session)
    owner_id = await _make_user(db_session, "teacher@example.com")
    classroom = await setup.create_class(
        owner_id, CreateClassRequest(name="Algorithms")
    )
    student_ids = [
        await _make_user(db_session, f"s{i}@example.com") for i in range(over_subscribe)
    ]
    # Commit the seed data so the concurrent sessions below can see the users.
    await db_session.commit()

    async def _enroll(student_id: int) -> bool:
        # Each concurrent task gets its own session, like separate requests.
        async with session_factory() as session:
            try:
                await CourseService(session).enroll(classroom.id, student_id)
                return True
            except APIException:
                return False

    results = await asyncio.gather(*(_enroll(sid) for sid in student_ids))

    assert sum(results) == cap
    assert await setup.count_enrollments(classroom.id) == cap
