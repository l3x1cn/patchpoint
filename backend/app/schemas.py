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
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM
    asset_tag: str | None = None
    location: str | None = None


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: int | None = None


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
    body: str = Field(min_length=1)


class CommentResponse(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    author_name: str
    body: str
    created_at: datetime


class TicketDetailResponse(TicketResponse):
    comments: list[CommentResponse]
