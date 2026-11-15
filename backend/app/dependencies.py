import sqlite3
from collections.abc import AsyncIterator
from contextlib import closing
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.config import Settings
from app.database import connect, fetch_one
from app.schemas import Role, UserResponse
from app.security import SESSION_COOKIE_NAME

BEARER_PREFIX = "Bearer "


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


type AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_db(settings: AppSettings) -> AsyncIterator[sqlite3.Connection]:
    with closing(connect(settings.database_path)) as conn:
        yield conn


type DbConnection = Annotated[sqlite3.Connection, Depends(get_db)]


async def get_current_user(request: Request, conn: DbConnection) -> UserResponse:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith(BEARER_PREFIX):
        token: str | None = authorization[len(BEARER_PREFIX) :]
    else:
        token = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = fetch_one(
        conn,
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    )
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session token")

    return UserResponse.model_validate(dict(row))


type CurrentUser = Annotated[UserResponse, Depends(get_current_user)]


async def require_agent(user: CurrentUser) -> UserResponse:
    if user.role != Role.AGENT:
        raise HTTPException(status_code=403, detail="Helpdesk agent role required")

    return user


type AgentUser = Annotated[UserResponse, Depends(require_agent)]
