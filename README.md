# MediVue Task Management API

A robust Task Management REST API built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**, featuring advanced filtering, tagging, deadlines, pagination, and full Swagger documentation.

---

### Run

```bash
docker-compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tasks` | Create a new task |
| `GET` | `/tasks` | List tasks (with filtering & pagination) |
| `GET` | `/tasks/{id}` | Get a single task |
| `PATCH` | `/tasks/{id}` | Partially update a task |
| `DELETE` | `/tasks/{id}` | Soft-delete a task |

### Example Requests

```bash
# Create a task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Fix bug", "priority": 4, "due_date": "2025-12-31", "tags": ["work", "urgent"]}'

# List high-priority incomplete tasks tagged "work"
curl "http://localhost:8000/tasks?completed=false&priority=4&tags=work"

# Partial update
curl -X PATCH http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'
```

## Project Structure

```
task-api/
├── app/
│   ├── main.py          # FastAPI app, middleware, exception handlers
│   ├── database.py      # SQLAlchemy engine & session
│   ├── models.py        # ORM models (Task, Tag, task_tags join table)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── crud.py          # Database operations
│   ├── exceptions.py    # Custom error handlers
│   └── routers/
│       └── tasks.py     # All task endpoints
├── tests/
│   ├── conftest.py      # Test fixtures (SQLite override)
│   └── test_tasks.py    # Full test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```


### Tagging: Join Table vs JSONB/ARRAY

**Chosen approach: Normalized Join Table** (`task_tags` many-to-many with a `tags` table).

The join table approach was chosen because:
1. Tags are deduplicated — `"work"` always resolves to the same `Tag` row (ID-stable).
2. SQL JOINs allow efficient `ANY OF` and `ALL OF` filtering.
3. It enforces referential integrity via foreign keys with `CASCADE` deletes.
4. Adding tag metadata (color, description) in the future requires zero schema migration.

**Trade-off**: Querying involves a JOIN, which is slightly slower than a single-table ARRAY lookup for very large datasets. For this scale, the JOIN overhead is negligible and the integrity benefits outweigh it.

### Soft Delete vs Hard Delete

**Chosen approach: Soft Delete** (setting `deleted = True` flag).

- Data is never lost; deleted tasks can be recovered or audited.
- Deletion is safer: clients can accidentally delete tasks, and soft delete enables an "undo" feature.
- Soft-deleted tasks are excluded from all `GET` queries transparently.
- **Trade-off**: The `tasks` table will accumulate deleted rows over time. In production, a background job or scheduled `VACUUM` could archive/purge old soft-deleted rows.

### Partial Updates (PATCH)

`PATCH` uses `model_dump(exclude_unset=True)` to extract only the fields present in the request body. Fields absent from the JSON payload are **never touched**, enabling safe partial updates (e.g., updating only `completed` without affecting `title` or `tags`).

### Indexing Strategy

The following database indexes are applied:

| Index | Columns | Reason |
|-------|---------|--------|
| `ix_tasks_priority` | `priority` | Frequently used as a filter |
| `ix_tasks_completed` | `completed` | Frequently used as a filter |
| `ix_tasks_deleted` | `deleted` | Every query filters by `deleted = false` |
| `ix_tasks_priority_completed` | `priority, completed` | Composite for combined filter queries |
| `ix_tags_name` | `name` | Tag lookups by name (unique) |

**Trade-off**: Each index speeds up reads but slightly slows INSERT/UPDATE operations and increases storage. The fields indexed here are used in almost every query, making the trade-off clearly worthwhile.