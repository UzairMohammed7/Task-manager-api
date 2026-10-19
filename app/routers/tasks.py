from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DbSession
from app.models import Task, TaskPriority, TaskStatus
from app.schemas import Page, TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_owned_task_or_404(db: DbSession, task_id: int, user_id: int) -> Task:
    """Fetch a task only if it belongs to user_id.

    Returns 404 (not 403) for other people's tasks, so the API doesn't reveal
    which task IDs exist. In M6 admins will bypass the owner filter.
    """
    task = db.scalar(select(Task).where(Task.id == task_id, Task.owner_id == user_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession, current_user: CurrentUser) -> Task:
    task = Task(**payload.model_dump(), owner_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def _escape_like(value: str) -> str:
    """Make %, _ and \\ in user input match literally inside a LIKE pattern."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=Page[TaskRead])
def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[TaskRead]:
    # Base filter: ownership first, so nothing below can widen access.
    conditions = [Task.owner_id == current_user.id]

    if status_ is not None:
        conditions.append(Task.status == status_)
    if priority is not None:
        conditions.append(Task.priority == priority)
    if search:
        pattern = f"%{_escape_like(search.strip())}%"
        conditions.append(
            or_(
                Task.title.ilike(pattern, escape="\\"),
                Task.description.ilike(pattern, escape="\\"),
            )
        )

    # Count uses the same conditions, so total matches the filtered result set.
    total = db.scalar(select(func.count()).select_from(Task).where(*conditions)) or 0

    rows = db.scalars(
        select(Task)
        .where(*conditions)
        .order_by(Task.created_at.desc(), Task.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return Page[TaskRead](
        items=[TaskRead.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )

@router.get("", response_model=list[TaskRead])
def list_tasks(db: DbSession, current_user: CurrentUser) -> list[Task]:
    # Filtering, search and pagination arrive in M5.
    stmt = select(Task).where(Task.owner_id == current_user.id).order_by(Task.id)
    return list(db.scalars(stmt))


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DbSession, current_user: CurrentUser) -> Task:
    return get_owned_task_or_404(db, task_id, current_user.id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int, payload: TaskUpdate, db: DbSession, current_user: CurrentUser
) -> Task:
    task = get_owned_task_or_404(db, task_id, current_user.id)

    # exclude_unset=True -> only fields the client actually sent.
    changes = payload.model_dump(exclude_unset=True)

    # title/status/priority are NOT NULL columns, so reject an explicit null.
    for field in ("title", "status", "priority"):
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    for field, value in changes.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession, current_user: CurrentUser) -> None:
    task = get_owned_task_or_404(db, task_id, current_user.id)
    db.delete(task)
    db.commit()