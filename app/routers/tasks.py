from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Task
from app.schemas import TaskCreate, TaskRead, TaskUpdate

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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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