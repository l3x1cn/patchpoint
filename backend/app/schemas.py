from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    EMPLOYEE = "employee"
    AGENT = "agent"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str
    full_name: str = Field(min_length=1)
    department: str = ""
    role: Role = Role.EMPLOYEE


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    department: str
    role: Role
    created_at: datetime
    password_hash: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    sqlite_version: str
    python_version: str
