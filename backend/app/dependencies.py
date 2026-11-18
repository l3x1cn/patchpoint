import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import closing
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.audit import log_security_event
from app.config import Settings
from app.database import connect
from app.schemas import Role, UserResponse
from app.security import SESSION_COOKIE_NAME
from app.sessions import SessionRejectedError, authenticate_session


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


type AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_db(settings: AppSettings) -> AsyncIterator[sqlite3.Connection]:
    with closing(connect(settings.database_path)) as conn:
        yield conn


type DbConnection = Annotated[sqlite3.Connection, Depends(get_db)]


async def get_current_user(
    request: Request, conn: DbConnection, settings: AppSettings
) -> UserResponse:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        return authenticate_session(conn, token, settings)
    except SessionRejectedError as exc:
        log_security_event(
            "session_rejected",
            request,
            level=logging.WARNING,
            reason=exc.reason,
            user_id=exc.user_id,
        )
        raise HTTPException(status_code=401, detail="Not authenticated") from exc


type CurrentUser = Annotated[UserResponse, Depends(get_current_user)]


async def require_agent(user: CurrentUser, request: Request) -> UserResponse:
    if user.role != Role.AGENT:
        log_security_event(
            "access_denied",
            request,
            level=logging.WARNING,
            user_id=user.id,
            reason="agent_role_required",
            path=request.url.path,
            ticket_id=None,
        )
        raise HTTPException(status_code=403, detail="Helpdesk agent role required")

    return user


type AgentUser = Annotated[UserResponse, Depends(require_agent)]
