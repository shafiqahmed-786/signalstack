from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import router as api_v1_router
from app.config import get_settings
from app.db.session import engine
from app.middleware.auth import ClerkAuthMiddleware
from app.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.middleware.request_id import RequestIDMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

settings = get_settings()


def configure_logging() -> None:
    """
    Configure structlog for structured JSON logging.

    In development (debug=True), uses ConsoleRenderer for human-readable output.
    In production, emits JSON to stdout for ingestion by log aggregators.
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.debug:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(settings.numeric_log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so SQLAlchemy / uvicorn logs go through structlog
    logging.basicConfig(
        format="%(message)s",
        level=settings.numeric_log_level,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    log = structlog.get_logger("app.lifespan")

    # ── Startup ────────────────────────────────────────────────
    log.info(
        "app.starting",
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Warm up the DB connection pool with a single connection
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        log.info("app.database_pool_ready")
    except Exception as db_exc:
        log.warning("app.database_unavailable", error=str(db_exc))

    # Warm up the Clerk JWKS client so the first request doesn't
    # pay the key-fetch latency
    try:
        from app.security.clerk import get_clerk_verifier
        get_clerk_verifier()  # Initializes the PyJWKClient singleton
        log.info("app.clerk_verifier_ready")
    except Exception as exc:
        log.warning("app.clerk_verifier_init_failed", error=str(exc))

    yield  # Application is running

    # ── Shutdown ───────────────────────────────────────────────
    log.info("app.shutting_down")
    await engine.dispose()
    log.info("app.database_connections_closed")


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Exception handlers ─────────────────────────────────────
    # Register BEFORE middleware so they can handle errors from middleware too
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Middleware (last added = outermost = first to run) ─────
    # Order: CORSMiddleware → ClerkAuthMiddleware → RequestIDMiddleware
    # Request flow: RequestIDMiddleware → ClerkAuthMiddleware → CORSMiddleware → route
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(ClerkAuthMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── Routers ────────────────────────────────────────────────
    app.include_router(api_v1_router)

    return app


app = create_app()