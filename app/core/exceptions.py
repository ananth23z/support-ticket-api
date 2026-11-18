"""
app/core/exceptions.py
======================
WHAT:  Our own exception classes + "handlers" that turn them into JSON responses.
WHY:   Services (business logic) should NOT know about HTTP. A service simply says
       `raise NotFoundError("Ticket not found")`. One central handler then converts
       that into an HTTP 404 response with a consistent JSON shape:

           {"error": "Not Found", "detail": "Ticket not found"}

       This is "CENTRALIZED EXCEPTION HANDLING": every error looks the same,
       and we don't repeat try/except in every endpoint.

ASP.NET ANALOGY:
    Like `app.UseExceptionHandler(...)` or a custom exception-handling middleware /
    `IExceptionHandler` that maps domain exceptions to ProblemDetails responses.

WHO USES IT:
    - services/*.py raise these exceptions
    - main.py registers `register_exception_handlers(app)`
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")


# ---------------------------------------------------------------------------
# 1) CUSTOM EXCEPTION CLASSES
# ---------------------------------------------------------------------------
class AppException(Exception):
    """Base class. Each subclass just picks an HTTP status code and a short title."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    error: str = "Bad Request"

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class BadRequestError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST          # 400: request makes no sense
    error = "Bad Request"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED         # 401: we don't know who you are
    error = "Unauthorized"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN            # 403: we know you, but you're not allowed
    error = "Forbidden"


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND            # 404: thing doesn't exist
    error = "Not Found"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT             # 409: e.g. email already registered
    error = "Conflict"


# ---------------------------------------------------------------------------
# 2) HANDLERS: functions FastAPI calls when an exception escapes an endpoint
# ---------------------------------------------------------------------------
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles every AppException subclass (NotFoundError, ForbiddenError, ...)."""
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "detail": exc.detail},
        headers=headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Pydantic validation failures (e.g. title too short, bad email) -> 422.
    FastAPI already does this by default; we override it only to keep the SAME
    JSON shape ("error" + "detail") as all our other errors.
    """
    # Build a simple, readable list like ["body.title: String should have at least 3 characters"]
    messages = [
        f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,  # 422 Unprocessable Content
        content={"error": "Validation Error", "detail": messages},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Safety net for bugs. We LOG the real error (for developers) but return a
    generic message (for users) so we never leak internal details/stack traces.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal Server Error", "detail": "Something went wrong."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Called once from main.py to plug all handlers into the app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
