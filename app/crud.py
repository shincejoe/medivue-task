from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Task, Tag, task_tags
from app.schemas import TaskCreate, TaskUpdate


def get_or_create_tags(db: Session, tag_names: List[str]) -> List[Tag]:
    tags = []
    for name in tag_names:
        name = name.strip().lower()
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def create_task(db: Session, data: TaskCreate) -> Task:
    task = Task(
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_date=data.due_date,
    )
    if data.tags:
        task.tags = get_or_create_tags(db, data.tags)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks(
    db: Session,
    completed: Optional[bool] = None,
    priority: Optional[int] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0,
):
    query = db.query(Task).filter(Task.deleted == False)

    if completed is not None:
        query = query.filter(Task.completed == completed)

    if priority is not None:
        query = query.filter(Task.priority == priority)

    if tags:
        normalized = [t.strip().lower() for t in tags if t.strip()]
        if normalized:
            # Match tasks that have ANY of the given tags
            query = (
                query.join(Task.tags)
                .filter(Tag.name.in_(normalized))
                .distinct()
            )

    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    return total, tasks


def get_task(db: Session, task_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id, Task.deleted == False).first()


def update_task(db: Session, task: Task, data: TaskUpdate) -> Task:
    update_data = data.model_dump(exclude_unset=True)

    if "tags" in update_data:
        tag_names = update_data.pop("tags") or []
        task.tags = get_or_create_tags(db, tag_names)

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    # Soft delete
    task.deleted = True
    db.commit()
