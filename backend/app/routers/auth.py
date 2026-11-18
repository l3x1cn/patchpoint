import logging
import sqlite3
from typing import Final

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool

from app.audit import log_security_event
from app.database import (
    DatabaseError,
    create_user,
    fetch_one,
    transaction,
    user_from_row,
)
from app.dependencies import AppSettings, CurrentUser, DbConnection
from app.schemas import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    Role,
    UserCreate,
    UserResponse,
)
from app.security import (
    SESSION_COOKIE_NAME,
    hash_password,
    simulate_password_check,
    verify_password,
)
from app.sessions import (
    clear_login_failures,
    create_session,
    end_session,
    is_login_blocked,
    record_login_failure,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

INVALID_CREDENTIALS: Final = "Invalid username or password"
USERNAME_TAKEN: Final = "Username is already taken"
LOGIN_BLOCKED: Final = "Too many failed login attempts. Try again later."


@router.post("/register", status_code=201)
async def register(payload: UserCreate, request: Request, conn: DbConnection) -> UserResponse:
    # Argon2 is CPU-bound, so it runs in a worker thread instead of on the event loop.
    password_hash = await run_in_threadpool(hash_password, payload.password)
    try:
        with transaction(conn):
            user_id = create_user(
                conn,
                username=payload.username,
                password_hash=password_hash,
                full_name=payload.full_name,
                department=payload.department,
                role=Role.EMPLOYEE,
            )
    except DatabaseError as exc:
        if not isinstance(exc.original, sqlite3.IntegrityError):
            raise
        log_security_event(
            "registration_conflict", request, level=logging.WARNING, username=payload.username
        )
        raise HTTPException(status_code=409, detail=USERNAME_TAKEN) from exc

    row = fetch_one(
        conn,
        "SELECT id, username, full_name, department, role, created_at FROM users WHERE id = ?",
        (user_id,),
    )
    if row is None:
        raise HTTPException(status_code=500, detail="User was not created")

    log_security_event(
        "user_registered",
        request,
        username=payload.username,
        user_id=user_id,
        role=Role.EMPLOYEE.value,
    )

    return user_from_row(row)


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    conn: DbConnection,
    settings: AppSettings,
) -> LoginResponse:
    if is_login_blocked(conn, payload.username, settings):
        log_security_event(
            "login_blocked", request, level=logging.WARNING, username=payload.username
        )
        raise HTTPException(
            status_code=429,
            detail=LOGIN_BLOCKED,
            headers={"Retry-After": str(settings.login_lockout_minutes * 60)},
        )

    # Count the attempt before the first await: between the check above and this write nothing
    # yields to the event loop, so concurrent guesses cannot all pass the lockout check. A
    # successful login clears the counter again. Only the pure Argon2 functions run in the pool;
    # the per-request SQLite connection stays on the event-loop thread.
    record_login_failure(conn, payload.username, settings)

    row = fetch_one(
        conn,
        "SELECT id, username, full_name, department, role, created_at, password_hash "
        "FROM users WHERE username = ?",
        (payload.username,),
    )
    if row is None:
        await run_in_threadpool(simulate_password_check, payload.password)
        log_security_event(
            "login_failed",
            request,
            level=logging.WARNING,
            username=payload.username,
            reason="unknown_user",
        )
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)

    password_matches = await run_in_threadpool(
        verify_password, payload.password, row["password_hash"]
    )
    if not password_matches:
        # The attempt was already counted above, so there is nothing left to record.
        log_security_event(
            "login_failed",
            request,
            level=logging.WARNING,
            username=payload.username,
            reason="bad_password",
        )
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)

    clear_login_failures(conn, payload.username)
    token = create_session(conn, user_id=row["id"], settings=settings)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.session_absolute_minutes * 60,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    log_security_event("login_succeeded", request, username=payload.username, user_id=row["id"])

    return LoginResponse(user=user_from_row(row))


@router.post("/logout")
async def logout(
    request: Request, response: Response, conn: DbConnection, settings: AppSettings
) -> MessageResponse:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user_id = end_session(conn, token) if token else None
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    log_security_event("logout", request, user_id=user_id)

    return MessageResponse(message="Logged out")


@router.get("/me")
async def get_me(user: CurrentUser) -> UserResponse:
    return user
