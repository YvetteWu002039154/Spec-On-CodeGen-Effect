import enum
from datetime import datetime
from typing import Dict, List, Optional, Set

from fastapi import WebSocket
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# -------------------------------------------------------------------
# Enumerations
# -------------------------------------------------------------------
class ProjectStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    archived = "archived"


class ServerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class ServerType(str, enum.Enum):
    physical = "physical"
    virtual = "virtual"
    container = "container"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    archived = "archived"


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


# -------------------------------------------------------------------
# SQLAlchemy ORM Models
# -------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.user)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")

    def __repr__(self):
        return f"<User {self.username}>"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String, default="#3498db")
    icon = Column(String, default="folder")
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.active)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")

    def __repr__(self):
        return f"<Project {self.name}>"


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    port = Column(Integer, default=22)
    os_type = Column(String, default="linux")
    description = Column(Text, nullable=True)
    ssh_username = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    ssh_password_encrypted = Column(String, nullable=True)
    agent_id = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    gpu_model = Column(String, nullable=True)
    status = Column(SQLEnum(ServerStatus), default=ServerStatus.offline)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics = relationship("MetricSnapshot", back_populates="server")
    tasks = relationship("Task", back_populates="server")

    def __repr__(self):
        return f"<Server {self.name}>"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.todo)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.medium)
    tags = Column(String, nullable=True, default="[]")  # JSON stored as string for simplicity
    order = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    server = relationship("Server", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.title}>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.action}>"


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    cpu_percent = Column(Float, nullable=True)
    cpu_per_core = Column(String, nullable=True)  # JSON list stored as text
    ram_percent = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    disk_read_mb = Column(Float, nullable=True)
    disk_write_mb = Column(Float, nullable=True)
    net_sent_mb = Column(Float, nullable=True)
    net_recv_mb = Column(Float, nullable=True)
    net_connections = Column(Integer, nullable=True)
    ping_ms = Column(Float, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    upload_speed_mbps = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    gpu_processes = Column(String, nullable=True)  # JSON stored as text
    timestamp = Column(DateTime, default=datetime.utcnow)

    server = relationship("Server", back_populates="metrics")

    def __repr__(self):
        return f"<MetricSnapshot server_id={self.server_id}>"


# -------------------------------------------------------------------
# Pydantic Schemas (Pydantic V2 style with model_config)
# -------------------------------------------------------------------
class ConfigMixin:
    model_config = ConfigDict(from_attributes=True)


# ----- User Schemas -----
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserRegister(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase, ConfigMixin):
    id: int
    is_active: bool
    role: UserRole
    created_at: Optional[datetime] = None


# ----- Project Schemas -----
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3498db"
    icon: str = "folder"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ConfigMixin):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    icon: str
    status: str
    owner_id: int
    task_count: int = 0
    completed_tasks: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ----- Server Schemas -----
class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int = 22
    os_type: str = "linux"
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


class ServerResponse(ConfigMixin):
    id: int
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int
    os_type: str
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[int] = None
    gpu_model: Optional[str] = None
    status: str
    last_heartbeat: Optional[datetime] = None
    task_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ----- Task Schemas -----
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    tags: List[str] = []
    due_date: Optional[datetime] = None  # mapped to deadline in DB
    project_id: Optional[int] = None
    server_id: Optional[int] = None


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    position: Optional[int] = None  # maps to order
    project_id: Optional[int] = None
    server_id: Optional[int] = None


class TaskReorder(BaseModel):
    task_id: int
    new_status: str
    new_order: int


class TaskResponse(TaskBase, ConfigMixin):
    id: int
    order: int
    assignee_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# ----- Authentication Schemas -----
class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ----- System Schemas -----
class SystemHealth(BaseModel):
    database: bool
    redis: bool
    status: str
    version: str


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_servers: int
    online_servers: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int


# ----- Settings (Pydantic Settings) -----
class Settings(BaseSettings):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: List[str] = ["*"]
    AGENT_SECRET: str
    SSH_KEY_PATH: str = "/etc/nexus/keys"

    class Config:
        case_sensitive = True
        env_file = ".env"


# -------------------------------------------------------------------
# WebSocket Manager
# -------------------------------------------------------------------
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
        conns = self.client_connections.get(server_id, set())
        conns.discard(websocket)
        if not conns:
            self.client_connections.pop(server_id, None)

    async def broadcast_to_clients(self, server_id: int, data: dict):
        for ws in self.client_connections.get(server_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                pass