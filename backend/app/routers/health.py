from fastapi import APIRouter

from app.database import fetch_one
from app.dependencies import DbConnection
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(conn: DbConnection) -> HealthResponse:
    fetch_one(conn, "SELECT 1")

    return HealthResponse(status="ok")
