from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard list response: the items on this page plus pagination metadata."""

    items: list[T]
    total: int      # matching rows across ALL pages
    limit: int
    offset: int