from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from src.auth.constants import BEARER_TOKEN_TYPE


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = BEARER_TOKEN_TYPE


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime
