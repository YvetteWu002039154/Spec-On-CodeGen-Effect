from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, Dict, List, Optional, Set

from pydantic import BaseModel, EmailStr, field_validator
from pydantic_settings import BaseSettings
from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from starlette.websockets import WebSocket

Base = declarative_base()


class ProjectStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    on_hold = "on_hold"
    archived = "archived"


class ServerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class ServerType(str, enum.Enum):
    physical = "physical"
    virtual = "virtual"
    cloud = "cloud"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskStatus(str, enum.Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    readonly = "readonly"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(SAEnum(UserRole), default=UserRole.user)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    color = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.active)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    port = Column(Integer, default=22)
    os_type = Column(String, nullable=True)
    description = Column(String, nullable=True)
    status = Column(SAEnum(ServerStatus), default=ServerStatus.offline)
    agent_id = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    ssh_username = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    ssh_password_encrypted = Column(String, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    gpu_model = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = relationship("Task", back_populates="server")
    metrics = relationship("MetricSnapshot", back_populates="server")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.backlog)
    priority = Column(SAEnum(TaskPriority), default=TaskPriority.medium)
    order = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    tags = Column(JSON, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    server = relationship("Server", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    cpu_percent = Column(Float, nullable=True)
    cpu_per_core = Column(JSON, nullable=True)
    ram_percent = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    disk_read_mb = Column(Float, nullable=True)
    disk_write_mb = Column(Float, nullable=True)
    net_recv_mb = Column(Float, nullable=True)
    net_sent_mb = Column(Float, nullable=True)
    net_connections = Column(Integer, nullable=True)
    ping_ms = Column(Float, nullable=True)
    upload_speed_mbps = Column(Float, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    gpu_processes = Column(JSON, nullable=True)

    server = relationship("Server", back_populates="metrics")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Pydantic models

class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    email: Annotated[str, EmailStr]
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[Annotated[str, EmailStr]] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3b82f6"
    icon: str = "folder"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    icon: str
    status: ProjectStatus
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    task_count: int = 0
    completed_tasks: int = 0

    class Config:
        from_attributes = True


class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: Optional[str] = None
    os_type: str = "linux"
    port: int = 22
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    description: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    os_type: Optional[str] = None
    port: Optional[int] = None
    description: Optional[str] = None
    status: Optional[ServerStatus] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None


class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int
    os_type: str
    description: Optional[str] = None
    status: ServerStatus
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[float] = None
    gpu_model: Optional[str] = None
    ssh_username: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    task_count: int = 0

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.medium
    status: TaskStatus = TaskStatus.backlog
    tags: List[str] = []
    project_id: Optional[int] = None
    server_id: Optional[int] = None


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    order: int
    assignee_id: Optional[int] = None

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    assignee_id: Optional[int] = None
    position: Optional[int] = None


class TaskReorder(BaseModel):
    task_id: int
    new_order: int
    new_status: str


class DashboardStats(BaseModel):
    total_projects: int = 0
    active_projects: int = 0
    total_servers: int = 0
    online_servers: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0


class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool


class MetricsConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    async def disconnect_agent(self, server_id: int):
        self.agent_connections.pop(server_id, None)

    async def connect_client(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    async def disconnect_client(self, websocket: WebSocket, server_id: int):
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict):
        if server_id in self.client_connections:
            for ws in self.client_connections[server_id]:
                await ws.send_json(data)


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
    CORS_ORIGINS: List[str] = ["*"]
    AGENT_SECRET: str = "agent-secret-key"
    SSH_KEY_PATH: str = "~/.ssh/id_rsa"

    class Config:
        env_file = ".env"
        case_sensitive = True