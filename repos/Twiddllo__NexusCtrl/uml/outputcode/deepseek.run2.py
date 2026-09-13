from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
import json

from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Float,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from starlette.websockets import WebSocket

# SQLAlchemy Base
Base = declarative_base()

# ------------------ Enums ------------------


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ServerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class ServerType(str, Enum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    CONTAINER = "container"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


# ------------------ ORM Models ------------------


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_per_core: Mapped[Optional[Union[List[float], Any]]] = mapped_column(JSON, nullable=True)
    ram_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_read_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_write_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_recv_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_sent_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_connections: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    download_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upload_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ping_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_used_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_processes: Mapped[Optional[Union[List[Dict[str, Any]], Any]]] = mapped_column(JSON, nullable=True)

    server: Mapped["Server"] = relationship("Server", back_populates="metrics")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3B82F6")
    icon: Mapped[str] = mapped_column(String(50), nullable=False, default="folder")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=ProjectStatus.ACTIVE.value)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project")


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    os_type: Mapped[str] = mapped_column(String(50), nullable=False, default="linux")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ssh_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ssh_password_encrypted: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ssh_key_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=ServerStatus.OFFLINE.value)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics: Mapped[List[MetricSnapshot]] = relationship("MetricSnapshot", back_populates="server")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="server")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=TaskStatus.TODO.value)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default=TaskPriority.MEDIUM.value)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[Optional[Union[List[str], Any]]] = mapped_column(JSON, nullable=True, default=list)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("servers.id"), nullable=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped[Optional[Project]] = relationship("Project", back_populates="tasks")
    server: Mapped[Optional[Server]] = relationship("Server", back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", back_populates="tasks")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects: Mapped[List[Project]] = relationship("Project", back_populates="owner")
    tasks: Mapped[List[Task]] = relationship("Task", back_populates="assignee")


# ------------------ Pydantic Schemas ------------------


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    role: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class Settings(BaseSettings):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AGENT_SECRET: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    CORS_ORIGINS: List[str] = ["*"]
    SSH_KEY_PATH: str = "~/.ssh/nexusctrl"

    class Config:
        case_sensitive: bool = False
        env_file: str = ".env"


class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_servers: int
    online_servers: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3B82F6"
    icon: str = "folder"


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    icon: str
    status: str
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    task_count: int = 0
    completed_tasks: int = 0

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None


class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int = 22
    os_type: str = "linux"
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None


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
    ram_total_gb: Optional[float] = None
    gpu_model: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    task_count: int = 0

    class Config:
        from_attributes = True


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


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    tags: List[str] = []


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    order: int = 0

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    tags: Optional[List[str]] = None
    position: Optional[int] = None


class TaskReorder(BaseModel):
    task_id: int
    new_status: str
    new_order: int


class MetricsConnectionManager:
    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    def disconnect_agent(self, server_id: int) -> None:
        self.agent_connections.pop(server_id, None)
        # Optionally close the WebSocket outside of this synchronous method

    async def connect_client(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        message = json.dumps(data)
        for ws in self.client_connections.get(server_id, set()):
            try:
                await ws.send_text(message)
            except Exception:
                # If sending fails, optionally disconnect the client
                pass