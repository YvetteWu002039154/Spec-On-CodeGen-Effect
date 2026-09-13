import enum
from datetime import datetime
from typing import List, Optional, Dict, Set, Any
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON, Enum as SQLEnum, Text
from sqlalchemy.orm import declarative_base, relationship
from fastapi import WebSocket

Base = declarative_base()

class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    COMPLETED = "COMPLETED"

class ServerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"

class ServerType(str, enum.Enum):
    LINUX = "LINUX"
    WINDOWS = "WINDOWS"

class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class Settings(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AGENT_SECRET: str = "secret"
    ALGORITHM: str = "HS256"
    API_PREFIX: str = "/api/v1"
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: List[str] = ["*"]
    DATABASE_URL: str = "sqlite:///./nexusctrl.db"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECRET_KEY: str = "supersecretkey"
    SSH_KEY_PATH: str = "~/.ssh/id_rsa"

    class Config:
        case_sensitive = True
        env_file = ".env"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    color = Column(String, nullable=True)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")

class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    port = Column(Integer, default=22)
    os_type = Column(String, nullable=False)
    ssh_username = Column(String, nullable=True)
    ssh_password_encrypted = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    status = Column(SQLEnum(ServerStatus), default=ServerStatus.OFFLINE)
    agent_id = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_gb = Column(Integer, nullable=True)
    gpu_model = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = relationship("Task", back_populates="server")
    metrics = relationship("MetricSnapshot", back_populates="server")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    tags = Column(JSON, default=list)
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

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    id = Column(Integer, primary_key=True, index=True)
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
    net_sent_mb = Column(Float, nullable=True)
    net_recv_mb = Column(Float, nullable=True)
    net_connections = Column(Integer, nullable=True)
    ping_ms = Column(Float, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    upload_speed_mbps = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    gpu_processes = Column(JSON, nullable=True)

    server = relationship("Server", back_populates="metrics")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

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
    icon: str
    color: str

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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    hostname: str
    ip_address: Optional[str] = None
    port: int
    os_type: str
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    os_type: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    status: Optional[str] = None

class ServerResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    hostname: str
    ip_address: Optional[str] = None
    port: int
    os_type: str
    ssh_username: Optional[str] = None
    status: str
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[int] = None
    gpu_model: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    task_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    tags: List[str] = []
    due_date: Optional[datetime] = None
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
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    position: Optional[int] = None

class TaskReorder(BaseModel):
    task_id: int
    new_order: int
    new_status: str

class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int] = None
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_servers: int
    online_servers: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int

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

    async def connect_client(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    def disconnect_agent(self, server_id: int):
        if server_id in self.agent_connections:
            del self.agent_connections[server_id]

    def disconnect_client(self, websocket: WebSocket, server_id: int):
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict):
        if server_id in self.client_connections:
            dead_connections = set()
            for connection in self.client_connections[server_id]:
                try:
                    await connection.send_json(data)
                except Exception:
                    dead_connections.add(connection)
            
            for dead in dead_connections:
                self.client_connections[server_id].discard(dead)