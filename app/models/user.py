from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import UserRole, db_enum
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))  # never plain text
    role: Mapped[UserRole] = mapped_column(db_enum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(default=True)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"