from enum import StrEnum


class ClassRelation(StrEnum):
    """How the current user relates to the classes being listed."""

    OWNER = "owner"  # classes the user teaches
    JOINER = "joiner"  # classes the user is enrolled in
