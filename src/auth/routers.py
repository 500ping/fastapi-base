from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import get_bearer_token, get_current_user
from src.auth.dtos.requests.auth import (
    LogoutRequest,
    RefreshRequest,
    SigninRequest,
    SignupRequest,
)
from src.auth.dtos.responses.auth import TokenResponse, UserResponse
from src.auth.models import User
from src.auth.openapi import (
    LOGOUT_RESPONSES,
    REFRESH_RESPONSES,
    SIGNIN_RESPONSES,
    SIGNUP_RESPONSES,
)
from src.auth.services import AuthService
from src.common.database.session import get_db
from src.common.dtos.responses.success import SuccessResponse

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/signup",
    response_model=SuccessResponse[UserResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    responses=SIGNUP_RESPONSES,
)
async def signup(req: SignupRequest, db: DbSession) -> SuccessResponse:
    user = await AuthService(db).signup(req)
    return SuccessResponse(
        status_code=status.HTTP_201_CREATED,
        msg="User created successfully",
        data=UserResponse.model_validate(user),
    )


@router.post(
    "/signin",
    response_model=SuccessResponse[TokenResponse],
    response_model_exclude_none=True,
    responses=SIGNIN_RESPONSES,
)
async def signin(req: SigninRequest, db: DbSession) -> SuccessResponse:
    tokens = await AuthService(db).signin(req)
    return SuccessResponse(msg="Signed in successfully", data=tokens)


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    response_model_exclude_none=True,
    responses=REFRESH_RESPONSES,
)
async def refresh(req: RefreshRequest, db: DbSession) -> SuccessResponse:
    tokens = await AuthService(db).refresh(req)
    return SuccessResponse(msg="Token refreshed successfully", data=tokens)


@router.post(
    "/logout",
    response_model=SuccessResponse,
    response_model_exclude_none=True,
    responses=LOGOUT_RESPONSES,
)
async def logout(
    req: LogoutRequest,
    db: DbSession,
    access_token: Annotated[str, Depends(get_bearer_token)],
    _: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse:
    await AuthService(db).logout(access_token, req.refresh_token)
    return SuccessResponse(msg="Logged out successfully")
