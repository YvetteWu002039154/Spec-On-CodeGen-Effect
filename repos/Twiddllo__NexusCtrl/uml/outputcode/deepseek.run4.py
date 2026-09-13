from __future__ import annotations

import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, relationship
from starlette.websockets import WebSocket

Base = declarative_base()


# ---------- ENUMS ----------
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    # provide a name attribute to match diagram
    name = property(lambda self: self.value)


class ServerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    name = property(lambda self: self.value)


class ServerType(str, Enum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    name = property(lambda self: self.value)


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    name = property(lambda self: self.value)


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"
    name = property(lambda self: self.value)


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    name = property(lambda self: self.value)


# ---------- DATABASE MODELS ----------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=False)
    resource_id = Column(Integer, nullable=True)
    resource_type = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default=UserRole.USER.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(100), default="folder")
    color = Column(String(7), default="#3B82F6")
    status = Column(String(20), default=ProjectStatus.ACTIVE.value)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.DONE.value)


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, default=22)
    os_type = Column(String(50), nullable=False)
    agent_id = Column(String(100), unique=True, nullable=True)
    agent_version = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    ssh_username = Column(String(50), nullable=True)
    ssh_key_path = Column(String(500), nullable=True)
    ssh_password_encrypted = Column(String(500), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    gpu_model = Column(String(100), nullable=True)
    status = Column(String(20), default=ServerStatus.OFFLINE.value)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    metrics = relationship("MetricSnapshot", back_populates="server")
    tasks = relationship("Task", back_populates="server")

    @property
    def task_count(self) -> int:
        return len(self.tasks)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    cpu_percent = Column(Float, nullable=True)
    cpu_per_core = Column(JSON, nullable=True)
    ram_percent = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    disk_read_mb = Column(Float, nullable=True)
    disk_write_mb = Column(Float, nullable=True)
    net_sent_mb = Column(Float, nullable=True)
    net_recv_mb = Column(Float, nullable=True)
    net_connections = Column(Integer, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    upload_speed_mbps = Column(Float, nullable=True)
    ping_ms = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    gpu_processes = Column(JSON, nullable=True)

    server = relationship("Server", back_populates="metrics")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=TaskStatus.TODO.value)
    priority = Column(String(20), default=TaskPriority.MEDIUM.value)
    due_date = Column(DateTime(timezone=True), nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    order = Column(Integer, default=0)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
    server = relationship("Server", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks", foreign_keys=[assignee_id])


# ---------- PYDANTIC SCHEMAS ----------
class DashboardStats(BaseModel):
    total_projects: int = 0
    active_projects: int = 0
    total_servers: int = 0
    online_servers: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0


class SystemHealth(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    database: bool = True
    redis: bool = True


# ---------- PROJECT SCHEMAS ----------
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "folder"
    color: str = "#3B82F6"


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
    task_count: int
    completed_tasks: int
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


# ---------- SERVER SCHEMAS ----------
class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int = 22
    os_type: str
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    description: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    os_type: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int
    os_type: str
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[int] = None
    gpu_model: Optional[str] = None
    status: str
    last_heartbeat: Optional[datetime.datetime] = None
    task_count: int
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


# ---------- TASK SCHEMAS ----------
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime.datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list)


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime.datetime] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    tags: Optional[List[str]] = None
    position: Optional[int] = None


class TaskReorder(BaseModel):
    task_id: int
    new_order: int
    new_status: str


class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int] = None
    order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


# ---------- USER SCHEMAS ----------
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


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    role: str
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


# ---------- AUTH SCHEMAS ----------
class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------- SETTINGS ----------
class Settings(BaseSettings):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AGENT_SECRET: str = "agent-secret-key"
    DATABASE_URL: str = "sqlite:///./nexusctrl.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    SSH_KEY_PATH: str = "./ssh_keys"

    class Config:
        case_sensitive = True
        env_file = ".env"


# ---------- METRICS CONNECTION MANAGER ----------
class MetricsConnectionManager:
    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    async def disconnect_agent(self, server_id: int) -> None:
        if server_id in self.agent_connections:
            await self.agent_connections[server_id].close()
            del self.agent_connections[server_id]

    async def connect_client(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        self.client_connections.setdefault(server_id, set()).add(websocket)

    async def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            await websocket.close()

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        clients = self.client_connections.get(server_id, [])
        for client in list(clients):
            try:
                await client.send_json(data)
            except Exception:
                # client disconnected
                await self.disconnect_client(client, server_id)