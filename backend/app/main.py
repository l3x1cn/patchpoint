import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.body_limit import RequestBodyLimitMiddleware

from app.audit import ERROR_LOGGER, configure_logging
from app.config import APP_VERSION, Settings
from app.database import DatabaseError, init_db
from app.middleware import SecurityHeadersMiddleware
from app.routers import auth, health, tickets


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = uuid.uuid4().hex
    ERROR_LOGGER.error(
        json.dumps(
            {
                "event": "internal_error",
                "error_id": error_id,
                "method": request.method,
                "path": request.url.path,
                "exception": type(exc).__name__,
                "sql": exc.sql if isinstance(exc, DatabaseError) else None,
            },
            sort_keys=True,
        ),
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": error_id},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_db(settings.database_path, with_demo_data=settings.seed_demo_data)
        yield

    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None
    app = FastAPI(
        title="PatchPoint API",
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.state.settings = settings

    # The last middleware added is the outermost, so CORS also covers 413 responses.
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=settings.max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
        max_age=600,
    )

    app.add_exception_handler(DatabaseError, internal_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(tickets.router)

    return app


app = create_app()
