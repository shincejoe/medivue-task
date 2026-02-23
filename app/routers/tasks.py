from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, PaginatedTaskResponse
from app.exceptions import not_found_response
import app.crud as crud

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=201,
    summary="Create a new task",
    responses={
        422: {
            "description": "Validation Failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Validation Failed",
                        "details": {"priority": "Must be between 1 and 5"},
                    }
                }
            },
        }
    },
)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task with the following fields:
    - **title**: Required, non-empty, max 200 chars
    - **description**: Optional
    - **priority**: 1–5 (5 is highest), defaults to 3
    - **due_date**: ISO format YYYY-MM-DD, must not be in the past
    - **tags**: Optional list of tag strings
    """
    return crud.create_task(db, data)


@router.get(
    "",
    response_model=PaginatedTaskResponse,
    summary="List tasks with filtering and pagination",
)
def list_tasks(
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority (1–5)"),
    tags: Optional[str] = Query(None, description="CSV list of tags to match (any), e.g. work,urgent"),
    limit: int = Query(20, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of tasks.

    - Filter by **completed** status, **priority**, or **tags** (CSV, matches any).
    - Use **limit** and **offset** for pagination.
    - Returns a paginated object with `total`, `limit`, `offset`, and `tasks`.
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    total, tasks = crud.get_tasks(
        db,
        completed=completed,
        priority=priority,
        tags=tag_list,
        limit=limit,
        offset=offset,
    )
    return PaginatedTaskResponse(total=total, limit=limit, offset=offset, tasks=tasks)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by ID",
    responses={404: {"description": "Task not found"}},
)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Return a single task by its ID, or 404 if not found."""
    task = crud.get_task(db, task_id)
    if not task:
        return not_found_response("Task")
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task",
    responses={404: {"description": "Task not found"}},
)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    """
    Partially update a task. Only fields provided in the request body are modified.

    You can update any combination of: title, description, priority, due_date, completed, tags.
    """
    task = crud.get_task(db, task_id)
    if not task:
        return not_found_response("Task")
    return crud.update_task(db, task, data)


@router.delete(
    "/{task_id}",
    status_code=204,
    summary="Soft-delete a task",
    responses={404: {"description": "Task not found"}},
)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Soft-delete a task by setting its `deleted` flag to true.
    The task is excluded from all future GET responses but remains in the database.
    """
    task = crud.get_task(db, task_id)
    if not task:
        return not_found_response("Task")
    crud.delete_task(db, task)
