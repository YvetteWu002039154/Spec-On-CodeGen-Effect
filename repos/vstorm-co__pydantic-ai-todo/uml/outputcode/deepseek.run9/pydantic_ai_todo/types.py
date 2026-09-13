from __future__ import annotations

import datetime
from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class Todo(BaseModel):
    """A full todo item."""
    active_form: str = ""
    content: str = ""
    depends_on: Optional[List[str]] = Field(default_factory=list)
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "blocked"] = "pending"


class TodoItem(BaseModel):
    """A partial update description for a todo."""
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[Literal["pending", "in_progress", "completed", "blocked"]] = None


class TodoStatusUpdate(BaseModel):
    """A request to update the status of a todo."""
    status: Optional[Literal["pending", "in_progress", "completed", "blocked"]] = None
    todo_id: Optional[str] = None

