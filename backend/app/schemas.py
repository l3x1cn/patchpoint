from datetime import datetime
from enum import StrEnum
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, password_policy_violation

USERNAME_PATTERN: Final = r"^[A-Za-z0-9._@+-]+$"
MAX_SQLITE_INTEGER: Final = 2**63 - 1


class Role(StrEnum):
    EMPLOYEE = "employee"
    AGENT = "agent"


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    full_name: str = Field(min_length=1, max_length=100)
    department: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def enforce_password_policy(self) -> Self:
        violation = password_policy_violation(self.password, self.username)
        if violation is not None:
            raise ValueError(violation)

        return self


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    department: str
    role: Role
    created_at: datetime


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class LoginResponse(BaseModel):
    user: UserResponse


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


class TicketCategory(StrEnum):
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    MONITOR = "monitor"
    PRINTER = "printer"
    PERIPHERAL = "peripheral"
    NETWORK = "network"
    OTHER = "other"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM
    asset_tag: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=100)


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: int | None = Field(default=None, ge=1, le=MAX_SQLITE_INTEGER)


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    asset_tag: str | None
    location: str | None
    reporter_id: int
    reporter_name: str
    assignee_id: int | None
    assignee_name: str | None
    created_at: datetime
    updated_at: datetime


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    author_name: str
    body: str
    created_at: datetime


class TicketDetailResponse(TicketResponse):
    comments: list[CommentResponse]
    comment_count: int
