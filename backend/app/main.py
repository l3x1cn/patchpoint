import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import APP_VERSION, Settings
from app.database import DatabaseError, init_db
from app.routers import auth, health


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app_settings = settings

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_db(app_settings.database_path, with_demo_data=app_settings.seed_demo_data)
        yield

    app = FastAPI(title="PatchPoint API", version=APP_VERSION, debug=True, lifespan=lifespan)
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(_: Request, exc: DatabaseError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "DatabaseError",
                "message": str(exc.original),
                "query": exc.sql,
                "params": list(exc.params),
                "database": str(app_settings.database_path.resolve()),
                "traceback": "".join(traceback.format_exception(exc)).splitlines(),
            },
        )

    app.include_router(health.router)
    app.include_router(auth.router)

    return app


app = create_app()
