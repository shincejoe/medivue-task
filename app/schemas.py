from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TagSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Task title (required, max 200 chars)")
    description: Optional[str] = Field(None, description="Optional task description")
    priority: int = Field(3, ge=1, le=5, description="Priority level 1 - 5 (5 is highest)")
    due_date: Optional[date] = Field(None, description="Due date in ISO format YYYY-MM-DD")
    tags: Optional[List[str]] = Field(default_factory=list, description="List of tag strings")

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v):
        if v is not None and v < date.today():
            raise ValueError("due_date must not be in the past")
        return v

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("title must not be empty or whitespace")
        return v.strip()


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    due_date: Optional[date] = None
    completed: Optional[bool] = None
    tags: Optional[List[str]] = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v):
        if v is not None and v < date.today():
            raise ValueError("due_date must not be in the past")
        return v

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("title must not be empty or whitespace")
        return v.strip() if v else v


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: int
    due_date: Optional[date]
    completed: bool
    tags: List[TagSchema]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTaskResponse(BaseModel):
    total: int
    limit: int
    offset: int
    tasks: List[TaskResponse]
