import enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    COMPLETED = "COMPLETED"


class ServerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


class ServerType(str, enum.Enum):
    PHYSICAL = "PHYSICAL"
    VIRTUAL = "VIRTUAL"
    CLOUD = "CLOUD"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"


class Settings(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    AGENT_SECRET: str
    ALGORITHM: str
    API_PREFIX: str
    APP_NAME: str
    APP_VERSION: str
    CORS_ORIGINS: List[str]
    DATABASE_URL: str
    DEBUG: bool
    HOST: str
    PORT: int
    REDIS_URL: str
    REFRESH_TOKEN_EXPIRE_DAYS: int
    SECRET_KEY: str
    SSH_KEY_PATH: str

    class Config:
        env_file = ".env"
        case_sensitive = True


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default=UserRole.USER.value)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    username = Column(String, unique=True, index=True, nullable=False)

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    color = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=False)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default=ProjectStatus.ACTIVE.value)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)
    gpu_model = Column(String, nullable=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    name = Column(String, nullable=False)
    os_type = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    ram_total_gb = Column(Integer, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    ssh_password_encrypted = Column(String, nullable=True)
    ssh_username = Column(String, nullable=True)
    status = Column(String, default=ServerStatus.OFFLINE.value)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = relationship("Task", back_populates="server")
    metrics = relationship("MetricSnapshot", back_populates="server")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)
    order = Column(Integer, default=0)
    priority = Column(String, default=TaskPriority.MEDIUM.value)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    status = Column(String, default=TaskStatus.TODO.value)
    tags = Column(JSON, default=list)
    title = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = relationship("User", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    server = relationship("Server", back_populates="tasks")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    cpu_per_core = Column(JSON, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    disk_read_mb = Column(Float, nullable=True)
    disk_write_mb = Column(Float, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_processes = Column(JSON, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    net_connections = Column(Integer, nullable=True)
    net_recv_mb = Column(Float, nullable=True)
    net_sent_mb = Column(Float, nullable=True)
    ping_ms = Column(Float, nullable=True)
    ram_percent = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    upload_speed_mbps = Column(Float, nullable=True)

    server = relationship("Server", back_populates="metrics")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    resource_id = Column(Integer, nullable=True)
    resource_type = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class DashboardStats(BaseModel):
    active_projects: int
    completed_tasks: int
    online_servers: int
    pending_tasks: int
    total_projects: int
    total_servers: int
    total_tasks: int


class ProjectCreate(BaseModel):
    color: str
    description: Optional[str] = None
    icon: str
    name: str


class ProjectResponse(BaseModel):
    color: str
    completed_tasks: int
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    icon: str
    id: int
    name: str
    owner_id: int
    status: str
    task_count: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    color: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


class ServerCreate(BaseModel):
    description: Optional[str] = None
    hostname: str
    ip_address: Optional[str] = None
    name: str
    os_type: str
    port: int
    ssh_key_path: Optional[str] = None
    ssh_username: Optional[str] = None


class ServerResponse(BaseModel):
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    gpu_model: Optional[str] = None
    hostname: str
    id: int
    ip_address: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    name: str
    os_type: str
    port: int
    ram_total_gb: Optional[int] = None
    ssh_username: Optional[str] = None
    status: str
    task_count: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ServerUpdate(BaseModel):
    description: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    name: Optional[str] = None
    os_type: Optional[str] = None
    port: Optional[int] = None
    ssh_key_path: Optional[str] = None
    ssh_username: Optional[str] = None
    status: Optional[str] = None


class SystemHealth(BaseModel):
    database: bool
    redis: bool
    status: str
    version: str


class TaskBase(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    status: TaskStatus
    tags: List[str] = Field(default_factory=list)
    title: str


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskReorder(BaseModel):
    new_order: int
    new_status: str
    task_id: int


class TaskResponse(TaskBase):
    assignee_id: Optional[int] = None
    created_at: datetime
    id: int
    order: int
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    position: Optional[int] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    title: Optional[str] = None


class TokenRefresh(BaseModel):
    refresh_token: str


class UserLogin(BaseModel):
    password: str
    username: str


class UserRegister(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str
    username: str


class UserResponse(BaseModel):
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    email: str
    full_name: Optional[str] = None
    id: int
    is_active: bool
    role: str
    username: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class UserUpdate(BaseModel):
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class MetricsConnectionManager:
    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    async def connect_client(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    def disconnect_agent(self, server_id: int) -> None:
        if server_id in self.agent_connections:
            del self.agent_connections[server_id]

    def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        if server_id in self.client_connections:
            dead_connections = set()
            for connection in self.client_connections[server_id]:
                try:
                    await connection.send_json(data)
                except Exception:
                    dead_connections.add(connection)
            
            for dead in dead_connections:
                self.disconnect_client(dead, server_id)