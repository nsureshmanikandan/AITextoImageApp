"""Application middleware.

Provides request ID injection and global exception handling
for consistent error responses.
"""

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that generates a unique request_id for each request.

    Attaches the request_id to request state and response headers.
    """

    async def dispatch(self, request: Request, call_next):
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Store in request state for access in handlers/services
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Add request_id to response headers
        response.headers["X-Request-ID"] = request_id

        return response


def _get_request_id(request: Request) -> str:
    """Extract request_id from request state, or generate a fallback."""
    try:
        return request.state.request_id
    except AttributeError:
        return str(uuid.uuid4())


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app.

    Maps specific exception types to appropriate HTTP status codes
    and returns a consistent error structure.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors → 422."""
        request_id = _get_request_id(request)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": str(exc.errors()),
                "request_id": request_id,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Handle ValueError (resource not found) → 404."""
        request_id = _get_request_id(request)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error_code": "NOT_FOUND",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(
        request: Request, exc: RuntimeError
    ) -> JSONResponse:
        """Handle RuntimeError (upstream service failure) → 502."""
        request_id = _get_request_id(request)
        logger.error(
            "Runtime error (request_id=%s): %s", request_id, str(exc)
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error_code": "SERVICE_ERROR",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all other exceptions → 500."""
        request_id = _get_request_id(request)
        logger.error(
            "Unhandled exception (request_id=%s): %s",
            request_id,
            str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An internal error occurred.",
                "request_id": request_id,
            },
        )
