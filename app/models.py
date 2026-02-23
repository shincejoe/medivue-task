from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    ForeignKey, Table, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

# Join table for many-to-many Task <-> Tag relationship
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    tasks = relationship("Task", secondary=task_tags, back_populates="tags")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String, nullable=True)
    priority = Column(Integer, nullable=False, default=1)
    due_date = Column(Date, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False)  # Soft delete flag
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tags = relationship("Tag", secondary=task_tags, back_populates="tasks")

    # Indexes for frequently filtered fields
    __table_args__ = (
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_completed", "completed"),
        Index("ix_tasks_deleted", "deleted"),
        Index("ix_tasks_priority_completed", "priority", "completed"),
    )
