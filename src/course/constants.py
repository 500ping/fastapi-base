# Maximum number of students allowed in a single class.
MAX_STUDENTS_PER_CLASS = 40

# Prefix for the per-class enrollment lock name (see distributed_lock).
ENROLL_LOCK_PREFIX = "class-enroll"


def enroll_lock_name(class_id: int) -> str:
    """Lock name serializing concurrent enrollments into one class."""
    return f"{ENROLL_LOCK_PREFIX}:{class_id}"
