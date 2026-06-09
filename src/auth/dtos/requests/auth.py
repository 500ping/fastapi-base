from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from src.auth.utils import normalize_email

NormalizedEmail = Annotated[EmailStr, AfterValidator(normalize_email)]

_REFRESH_TOKEN_EXAMPLE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2gifQ"
    ".h3fAo0vQ1m2bq9rXk7Zt6yJ8sN0pLwQeR4uT5vW6xY"
)


class SignupRequest(BaseModel):
    email: NormalizedEmail = Field(examples=["user@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["supersecret"])


class SigninRequest(BaseModel):
    email: NormalizedEmail = Field(examples=["user@example.com"])
    password: str = Field(examples=["supersecret"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(examples=[_REFRESH_TOKEN_EXAMPLE])


class LogoutRequest(BaseModel):
    refresh_token: str = Field(examples=[_REFRESH_TOKEN_EXAMPLE])
