import enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Annotated

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

# ==========================================
# Enums
# ==========================================

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"

class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

class ServerType(str, enum.Enum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    CLOUD = "cloud"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


# ==========================================
# Database Models (SQLAlchemy)
# ==========================================

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    username = Column(String, unique=True, index=True, nullable=False)

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    color = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
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
    description = Column(Text, nullable=True)
    gpu_model = Column(String, nullable=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    name = Column(String, nullable=False)
    os_type = Column(String, nullable=False)
    port = Column(Integer, default=22)
    ram_total_gb = Column(Integer, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    ssh_password_encrypted = Column(String, nullable=True)
    ssh_username = Column(String, nullable=True)
    status = Column(SQLEnum(ServerStatus), default=ServerStatus.OFFLINE)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics = relationship("MetricSnapshot", back_populates="server")
    tasks = relationship("Task", back_populates="server")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
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
    server_id = Column(Integer, ForeignKey("servers.id"))
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


# ==========================================
# Pydantic Schemas
# ==========================================

class Settings(BaseModel):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AGENT_SECRET: str = "secret"
    ALGORITHM: str = "HS256"
    API_PREFIX: str = "/api/v1"
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: List[str] = []
    DATABASE_URL: str = "sqlite:///./nexus.db"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECRET_KEY: str = "supersecretkey"
    SSH_KEY_PATH: str = "~/.ssh/id_rsa"

    class Config:
        case_sensitive: bool = True
        env_file: str = ".env"


class DashboardStats(BaseModel):
    active_projects: int
    completed_tasks: int
    online_servers: int
    pending_tasks: int
    total_projects: int
    total_servers: int
    total_tasks: int


class SystemHealth(BaseModel):
    database: bool
    redis: bool
    status: str
    version: str


class UserLogin(BaseModel):
    password: str
    username: str


class UserRegister(BaseModel):
    email: Annotated[EmailStr, Field(description="User email address")]
    full_name: Optional[str] = None
    password: str
    username: str


class UserUpdate(BaseModel):
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    avatar_url: Optional[str]
    created_at: Optional[datetime]
    email: str
    full_name: Optional[str]
    id: int
    is_active: bool
    role: str
    username: str

    class Config:
        from_attributes: bool = True


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class ProjectCreate(BaseModel):
    color: str
    description: Optional[str] = None
    icon: str
    name: str


class ProjectUpdate(BaseModel):
    color: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    color: str
    completed_tasks: int
    created_at: Optional[datetime]
    description: Optional[str]
    icon: str
    id: int
    name: str
    owner_id: int
    status: str
    task_count: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes: bool = True


class ServerCreate(BaseModel):
    description: Optional[str] = None
    hostname: str
    ip_address: Optional[str] = None
    name: str
    os_type: str
    port: int
    ssh_key_path: Optional[str] = None
    ssh_username: Optional[str] = None


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


class ServerResponse(BaseModel):
    agent_id: Optional[str]
    agent_version: Optional[str]
    cpu_cores: Optional[int]
    created_at: Optional[datetime]
    description: Optional[str]
    gpu_model: Optional[str]
    hostname: str
    id: int
    ip_address: Optional[str]
    last_heartbeat: Optional[datetime]
    name: str
    os_type: str
    port: int
    ram_total_gb: Optional[int]
    ssh_username: Optional[str]
    status: str
    task_count: int
    updated_at: Optional[datetime]

    class Config:
        from_attributes: bool = True


class TaskBase(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    status: TaskStatus
    tags: List[str] = []
    title: str


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


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


class TaskReorder(BaseModel):
    new_order: int
    new_status: str
    task_id: int


class TaskResponse(TaskBase):
    assignee_id: Optional[int]
    created_at: datetime
    id: int
    order: int
    updated_at: datetime

    class Config:
        from_attributes: bool = True


# ==========================================
# Connection Manager
# ==========================================

class WebSocket:
    """Mock WebSocket class for type hinting and basic structure."""
    async def send_json(self, data: dict):
        pass
    async def close(self):
        pass


class MetricsConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int):
        self.agent_connections[server_id] = websocket

    async def connect_client(self, websocket: WebSocket, server_id: int):
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
            for connection in self.client_connections[server_id]:
                await connection.send_json(data)


if __name__ == "__main__":
    # Simple instantiation to verify the code runs without errors
    settings = Settings()
    manager = MetricsConnectionManager()
    print("NexusCtrl models and schemas initialized successfully.")