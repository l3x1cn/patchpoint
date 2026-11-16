import sqlite3

from fastapi import APIRouter, HTTPException, Response

from app.database import DatabaseError, create_user, execute, fetch_one, utc_now_iso
from app.dependencies import CurrentUser, DbConnection
from app.schemas import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    UserCreate,
    UserResponse,
)
from app.security import SESSION_COOKIE_NAME, generate_session_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(payload: UserCreate, conn: DbConnection) -> UserResponse:
    try:
        user_id = create_user(
            conn,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
            department=payload.department,
            role=payload.role,
        )
    except DatabaseError as exc:
        if isinstance(exc.original, sqlite3.IntegrityError):
            raise HTTPException(
                status_code=409, detail=f"Registration failed: {exc.original}"
            ) from exc
        raise

    row = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
    if row is None:
        raise HTTPException(status_code=500, detail="User was not created")

    return UserResponse.model_validate(dict(row))


@router.post("/login")
async def login(payload: LoginRequest, response: Response, conn: DbConnection) -> LoginResponse:
    row = fetch_one(conn, "SELECT * FROM users WHERE username = ?", (payload.username,))
    if row is None:
        raise HTTPException(status_code=404, detail=f"User '{payload.username}' does not exist")
    if not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = generate_session_token(payload.username)
    execute(
        conn,
        "INSERT OR IGNORE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, row["id"], utc_now_iso()),
    )
    response.set_cookie(key=SESSION_COOKIE_NAME, value=token)

    return LoginResponse(token=token, user=UserResponse.model_validate(dict(row)))


@router.post("/logout")
async def logout(response: Response) -> MessageResponse:
    response.delete_cookie(SESSION_COOKIE_NAME)
    return MessageResponse(message="Logged out")


@router.get("/me")
async def get_me(user: CurrentUser) -> UserResponse:
    return user
