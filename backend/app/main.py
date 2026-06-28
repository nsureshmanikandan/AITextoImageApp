"""FastAPI application factory and entry point.

Wires together all routers, middleware, exception handlers, and CORS config.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.middleware import RequestIdMiddleware, register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - create tables on startup."""
    from app.database import create_tables
    await create_tables()
    yield


def create_app() -> FastAPI:
    """Application factory for the AI Image Generation Platform."""
    app = FastAPI(
        title="AI Image Generation Platform",
        description="Generate high-quality images from natural language descriptions",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Register middleware (order matters: first added = outermost)
    app.add_middleware(RequestIdMiddleware)

    # Enable CORS for the frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Register global exception handlers
    register_exception_handlers(app)

    # Include all API v1 routers
    app.include_router(api_router)

    return app


app = create_app()
