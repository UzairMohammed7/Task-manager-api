from fastapi import APIRouter

from app.deps import CurrentUser
from app.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser):
    return current_user