from enum import StrEnum


class ExceptionMessageEnum(StrEnum):
    DEFAULT = "Unhandled Error"

    # Auth
    EMAIL_ALREADY_REGISTERED = "Email already registered"
    INVALID_CREDENTIALS = "Invalid email or password"
    INVALID_TOKEN = "Could not validate token"
    TOKEN_REVOKED = "Token has been revoked"
    USER_NOT_FOUND = "User not found"
    INACTIVE_USER = "Inactive user"

    # Course
    CLASS_NOT_FOUND = "Class not found"
    CLASS_FULL = "Class has reached its maximum capacity"
    ALREADY_ENROLLED = "Already enrolled in this class"

    # Infrastructure
    LOCK_UNAVAILABLE = "Service is busy, please try again"
