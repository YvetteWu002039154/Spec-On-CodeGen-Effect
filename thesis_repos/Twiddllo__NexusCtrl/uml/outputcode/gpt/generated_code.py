from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


class WebSocket:
    def __init__(self) -> None:
        self._accepted: bool = False
        self._sent: List[Any] = []

    async def accept(self) -> None:
        self._accepted = True

    async def send_json(self, data: Any) -> None:
        self._sent.append(data)

    @property
    def accepted(self) -> bool:
        return self._accepted

    @property
    def sent(self) -> List[Any]:
        return list(self._sent)


@dataclass
class Base:
    id: Optional[int] = None


class ProjectStatus(str, Enum):
    name = "name"


class ServerStatus(str, Enum):
    name = "name"


class ServerType(str, Enum):
    name = "name"


class TaskPriority(str, Enum):
    name = "name"


class TaskStatus(str, Enum):
    name = "name"


class UserRole(str, Enum):
    name = "name"


@dataclass
class AuditLog(Base):
    action: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    resource_id: Optional[int] = None
    resource_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    user_id: Optional[int] = None


@dataclass
class User(Base):
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    hashed_password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    updated_at: Optional[datetime] = None
    username: Optional[str] = None
    projects: List["Project"] = field(default_factory=list)
    tasks: List["Task"] = field(default_factory=list)


@dataclass
class Project(Base):
    color: Optional[str] = None
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    name: Optional[str] = None
    owner: Optional[User] = None
    owner_id: Optional[int] = None
    status: Optional[str] = None
    updated_at: Optional[datetime] = None
    tasks: List["Task"] = field(default_factory=list)


@dataclass
class Server(Base):
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    gpu_model: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    name: Optional[str] = None
    os_type: Optional[str] = None
    port: Optional[int] = None
    ram_total_gb: Optional[int] = None
    ssh_key_path: Optional[str] = None
    ssh_password_encrypted: Optional[str] = None
    ssh_username: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[datetime] = None
    metrics: List["MetricSnapshot"] = field(default_factory=list)
    tasks: List["Task"] = field(default_factory=list)


@dataclass
class MetricSnapshot(Base):
    cpu_per_core: Any = None
    cpu_percent: Any = None
    disk_percent: Any = None
    disk_read_mb: Any = None
    disk_write_mb: Any = None
    download_speed_mbps: Any = None
    gpu_memory_percent: Any = None
    gpu_memory_used_mb: Any = None
    gpu_percent: Any = None
    gpu_processes: Any = None
    gpu_temperature: Any = None
    net_connections: Any = None
    net_recv_mb: Any = None
    net_sent_mb: Any = None
    ping_ms: Any = None
    ram_percent: Any = None
    ram_total_gb: Any = None
    ram_used_gb: Any = None
    server: Optional[Server] = None
    server_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    upload_speed_mbps: Any = None


@dataclass
class Task(Base):
    assignee: Optional[User] = None
    assignee_id: Optional[int] = None
    created_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    order: Optional[int] = None
    priority: Any = None
    project: Optional[Project] = None
    project_id: Optional[int] = None
    server: Optional[Server] = None
    server_id: Optional[int] = None
    status: Any = None
    tags: Any = None
    title: Optional[str] = None
    updated_at: Optional[datetime] = None


@dataclass
class DashboardStats:
    active_projects: int
    completed_tasks: int
    online_servers: int
    pending_tasks: int
    total_projects: int
    total_servers: int
    total_tasks: int


@dataclass
class SystemHealth:
    database: bool
    redis: bool
    status: str
    version: str


@dataclass
class ProjectCreate:
    color: str
    description: Optional[str]
    icon: str
    name: str


@dataclass
class ProjectUpdate:
    color: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


@dataclass
class ProjectResponse:
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


@dataclass
class ServerCreate:
    description: Optional[str]
    hostname: str
    ip_address: Optional[str]
    name: str
    os_type: str
    port: int
    ssh_key_path: Optional[str]
    ssh_username: Optional[str]


@dataclass
class ServerUpdate:
    description: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    name: Optional[str] = None
    os_type: Optional[str] = None
    port: Optional[int] = None
    ssh_key_path: Optional[str] = None
    ssh_username: Optional[str] = None
    status: Optional[str] = None


@dataclass
class ServerResponse:
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


@dataclass
class TaskBase:
    description: Optional[str]
    due_date: Optional[datetime]
    priority: Any
    project_id: Optional[int]
    server_id: Optional[int]
    status: Any
    tags: List[str]
    title: str


@dataclass
class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


@dataclass
class TaskUpdate:
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    position: Optional[int] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    title: Optional[str] = None


@dataclass
class TaskReorder:
    new_order: int
    new_status: str
    task_id: int


@dataclass
class TaskResponse(TaskBase):
    assignee_id: Optional[int]
    created_at: datetime
    id: int
    order: int
    updated_at: datetime

    class Config:
        from_attributes: bool = True


@dataclass
class UserLogin:
    password: str
    username: str


@dataclass
class UserRegister:
    email: str
    full_name: Optional[str]
    password: str
    username: str


@dataclass
class UserUpdate:
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None


@dataclass
class UserResponse:
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


@dataclass
class TokenRefresh:
    refresh_token: str


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class Settings:
    class Config:
        case_sensitive: bool = True
        env_file: str = ".env"

    def __init__(
        self,
        ACCESS_TOKEN_EXPIRE_MINUTES: int,
        AGENT_SECRET: str,
        ALGORITHM: str,
        API_PREFIX: str,
        APP_NAME: str,
        APP_VERSION: str,
        CORS_ORIGINS: List[str],
        DATABASE_URL: str,
        DEBUG: bool,
        HOST: str,
        PORT: int,
        REDIS_URL: str,
        REFRESH_TOKEN_EXPIRE_DAYS: int,
        SECRET_KEY: str,
        SSH_KEY_PATH: str,
    ) -> None:
        self.ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
        self.AGENT_SECRET = AGENT_SECRET
        self.ALGORITHM = ALGORITHM
        self.API_PREFIX = API_PREFIX
        self.APP_NAME = APP_NAME
        self.APP_VERSION = APP_VERSION
        self.CORS_ORIGINS = CORS_ORIGINS
        self.DATABASE_URL = DATABASE_URL
        self.DEBUG = DEBUG
        self.HOST = HOST
        self.PORT = PORT
        self.REDIS_URL = REDIS_URL
        self.REFRESH_TOKEN_EXPIRE_DAYS = REFRESH_TOKEN_EXPIRE_DAYS
        self.SECRET_KEY = SECRET_KEY
        self.SSH_KEY_PATH = SSH_KEY_PATH


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
        self.agent_connections.pop(server_id, None)

    def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        conns = self.client_connections.get(server_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self.client_connections.pop(server_id, None)

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        conns = self.client_connections.get(server_id)
        if not conns:
            return
        for ws in list(conns):
            await ws.send_json(data)