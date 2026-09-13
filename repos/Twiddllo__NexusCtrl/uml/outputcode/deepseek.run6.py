from __future__ import annotations
import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, Float, JSON, Text, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from starlette.websockets import WebSocket


# ---------- ENUMS ----------
class ProjectStatus(str, Enum):
    # placeholders; add values as needed
    active = "active"
    completed = "completed"
    archived = "archived"


class ServerStatus(str, Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class ServerType(str, Enum):
    physical = "physical"
    virtual = "virtual"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


# ---------- SQLAlchemy Base ----------
class Base(DeclarativeBase):
    pass


# ---------- ORM MODELS ----------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[UserRole] = mapped_column(default=UserRole.user)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    projects: Mapped[List["Project"]] = relationship(back_populates="owner")
    tasks: Mapped[List["Task"]] = relationship(back_populates="assignee", foreign_keys="Task.assignee_id")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(50), default="folder")
    color: Mapped[str] = mapped_column(String(7), default="#000000")
    status: Mapped[ProjectStatus] = mapped_column(default=ProjectStatus.active)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    hostname: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    port: Mapped[int] = mapped_column(Integer, default=22)
    os_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[ServerStatus] = mapped_column(default=ServerStatus.offline)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ssh_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ssh_key_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ssh_password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ram_total_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gpu_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_heartbeat: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    metrics: Mapped[List["MetricSnapshot"]] = relationship(back_populates="server")
    tasks: Mapped[List["Task"]] = relationship(back_populates="server")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_per_core: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_read_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_write_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_sent_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_recv_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_connections: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    download_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upload_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ping_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_used_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_processes: Mapped[Optional[List[Dict]]] = mapped_column(JSON, nullable=True)

    server: Mapped["Server"] = relationship(back_populates="metrics")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.todo)
    priority: Mapped[TaskPriority] = mapped_column(default=TaskPriority.medium)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deadline: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    server_id: Mapped[Optional[int]] = mapped_column(ForeignKey("servers.id"), nullable=True)

    assignee: Mapped[Optional["User"]] = relationship(back_populates="tasks", foreign_keys=[assignee_id])
    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    server: Mapped[Optional["Server"]] = relationship(back_populates="tasks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# ---------- PYDANTIC SCHEMAS ----------
class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str


class UserUpdate(BaseModel):
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    role: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "folder"
    color: str = "#000000"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    icon: str
    color: str
    status: str
    owner_id: int
    task_count: int = 0
    completed_tasks: int = 0
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int = 22
    os_type: str
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    os_type: Optional[str] = None
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    status: Optional[str] = None


class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int
    os_type: str
    status: str
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[int] = None
    gpu_model: Optional[str] = None
    last_heartbeat: Optional[datetime.datetime] = None
    task_count: int = 0
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime.datetime] = Field(None, alias="deadline")
    tags: List[str] = []

    class Config:
        populate_by_name = True
        from_attributes = True


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime.datetime] = Field(None, alias="deadline")
    tags: Optional[List[str]] = None
    position: Optional[int] = None

    class Config:
        populate_by_name = True


class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int] = None
    order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class TaskReorder(BaseModel):
    task_id: int
    new_status: str
    new_order: int


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_servers: int
    online_servers: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int


class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool


# ---------- SETTINGS ----------
class Settings(BaseSettings):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./nexusctrl.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    AGENT_SECRET: str = "agent-secret-change-me"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    SSH_KEY_PATH: str = "./keys"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# ---------- METRICS CONNECTION MANAGER ----------
class MetricsConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    def disconnect_agent(self, server_id: int):
        self.agent_connections.pop(server_id, None)

    async def connect_client(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    def disconnect_client(self, websocket: WebSocket, server_id: int):
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict):
        if server_id in self.client_connections:
            for ws in self.client_connections[server_id].copy():
                await ws.send_json(data)