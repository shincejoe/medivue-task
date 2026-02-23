from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details[field] = error["msg"]
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Failed", "details": details},
    )


def not_found_response(resource: str = "Task"):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "details": {resource.lower(): f"{resource} not found"}},
    )
