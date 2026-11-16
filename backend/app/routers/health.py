import platform

from fastapi import APIRouter

from app.config import APP_VERSION
from app.database import fetch_one
from app.dependencies import AppSettings, DbConnection
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(settings: AppSettings, conn: DbConnection) -> HealthResponse:
    row = fetch_one(conn, "SELECT sqlite_version() AS version")

    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        database=str(settings.database_path.resolve()),
        sqlite_version=str(row["version"]) if row is not None else "unknown",
        python_version=platform.python_version(),
    )
