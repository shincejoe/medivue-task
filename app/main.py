from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.database import engine, Base
from app.routers import tasks
from app.exceptions import validation_exception_handler

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MediVue Task Management API",
    description=(
        "A robust Task Management API with advanced filtering, tagging, and deadlines.\n\n"
        "## Features\n"
        "- Create, read, update, and soft-delete tasks\n"
        "- Filter by completion status, priority, and tags (any-match, CSV)\n"
        "- Paginated list responses\n"
        "- Many-to-many tagging with a normalized join table\n"
    ),
    version="1.0.0",
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(tasks.router)
