import enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def db_enum(enum_cls: type[enum.Enum]) -> SAEnum:
    """Store enums as plain strings holding the *value* ("in_progress").

    native_enum=False -> VARCHAR column on every database, so adding a value
    later doesn't require altering a Postgres ENUM type.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda e: [member.value for member in e],
    )