from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import get_current_user
from src.auth.models import User
from src.common.database.session import get_db
from src.common.dtos.responses.success import Pagination, SuccessResponse
from src.course.constants import MAX_STUDENTS_PER_CLASS
from src.course.dtos.requests.course import CreateClassRequest, ListClassesParams
from src.course.dtos.responses.course import (
    ClassResponse,
    EnrollmentResponse,
    StudentResponse,
)
from src.course.models import ClassRoom
from src.course.openapi import (
    CREATE_CLASS_RESPONSES,
    ENROLL_RESPONSES,
    GET_CLASS_RESPONSES,
    LIST_CLASSES_RESPONSES,
    LIST_STUDENTS_RESPONSES,
)
from src.course.services import CourseService

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _class_response(classroom: ClassRoom, enrolled_count: int) -> ClassResponse:
    return ClassResponse(
        id=classroom.id,
        name=classroom.name,
        teacher_id=classroom.teacher_id,
        capacity=MAX_STUDENTS_PER_CLASS,
        enrolled_count=enrolled_count,
        created_at=classroom.created_at,
    )


@router.post(
    "/classes",
    response_model=SuccessResponse[ClassResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    responses=CREATE_CLASS_RESPONSES,
)
async def create_class(
    req: CreateClassRequest, db: DbSession, user: CurrentUser
) -> SuccessResponse:
    classroom = await CourseService(db).create_class(user.id, req)
    return SuccessResponse(
        status_code=status.HTTP_201_CREATED,
        msg="Class created successfully",
        data=_class_response(classroom, enrolled_count=0),
    )


@router.get(
    "/classes",
    response_model=SuccessResponse[list[ClassResponse]],
    response_model_exclude_none=True,
    responses=LIST_CLASSES_RESPONSES,
)
async def list_classes(
    db: DbSession,
    user: CurrentUser,
    params: Annotated[ListClassesParams, Query()],
) -> SuccessResponse:
    rows, total = await CourseService(db).list_classes(
        user.id, params.relation, params.page, params.size
    )
    return SuccessResponse(
        msg="Classes retrieved successfully",
        data=[_class_response(classroom, count) for classroom, count in rows],
        pagination=Pagination(page=params.page, size=params.size, total=total),
    )


@router.get(
    "/classes/{class_id}",
    response_model=SuccessResponse[ClassResponse],
    response_model_exclude_none=True,
    responses=GET_CLASS_RESPONSES,
)
async def get_class(class_id: int, db: DbSession, _: CurrentUser) -> SuccessResponse:
    service = CourseService(db)
    classroom = await service.get_class_or_404(class_id)
    enrolled_count = await service.count_enrollments(class_id)
    return SuccessResponse(
        msg="Class retrieved successfully",
        data=_class_response(classroom, enrolled_count),
    )


@router.get(
    "/classes/{class_id}/students",
    response_model=SuccessResponse[list[StudentResponse]],
    response_model_exclude_none=True,
    responses=LIST_STUDENTS_RESPONSES,
)
async def list_students(
    class_id: int, db: DbSession, _: CurrentUser
) -> SuccessResponse:
    rows = await CourseService(db).list_students(class_id)
    return SuccessResponse(
        msg="Students retrieved successfully",
        data=[
            StudentResponse(id=user.id, email=user.email, enrolled_at=enrolled_at)
            for user, enrolled_at in rows
        ],
    )


@router.post(
    "/classes/{class_id}/enroll",
    response_model=SuccessResponse[EnrollmentResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    responses=ENROLL_RESPONSES,
)
async def enroll(class_id: int, db: DbSession, user: CurrentUser) -> SuccessResponse:
    # The current user enrolls themselves as a student.
    enrollment = await CourseService(db).enroll(class_id, user.id)
    return SuccessResponse(
        status_code=status.HTTP_201_CREATED,
        msg="Enrolled successfully",
        data=EnrollmentResponse.model_validate(enrollment),
    )
