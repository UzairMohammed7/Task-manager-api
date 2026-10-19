from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import TaskPriority, TaskStatus, db_enum
from app.models.mixins import TimestampMixin
from app.models.user import User


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[TaskStatus] = mapped_column(
        db_enum(TaskStatus), default=TaskStatus.TODO, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        db_enum(TaskPriority), default=TaskPriority.MEDIUM, index=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, default=None)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    owner: Mapped[User] = relationship(back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status.value}>"