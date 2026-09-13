from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union


class WebSocket:
    async def accept(self) -> None:
        return None

    async def send_json(self, data: Any) -> None:
        return None

    async def close(self) -> None:
        return None


class Base:
    pass


@dataclass
class AuditLog(Base):
    action: Any = None
    details: Any = None
    id: Any = None
    ip_address: Any = None
    resource_id: Any = None
    resource_type: Any = None
    timestamp: Any = None
    user_id: Any = None


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
    id: Any = None
    net_connections: Any = None
    net_recv_mb: Any = None
    net_sent_mb: Any = None
    ping_ms: Any = None
    ram_percent: Any = None
    ram_total_gb: Any = None
    ram_used_gb: Any = None
    server: Any = None
    server_id: Any = None
    timestamp: Any = None
    upload_speed_mbps: Any = None


class MetricsConnectionManager:
    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        if server_id in self.agent_connections:
            try:
                await self.agent_connections[server_id].close()
            except Exception:
                pass
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
        dead: List[WebSocket] = []
        for ws in list(conns):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)
        if not conns:
            self.client_connections.pop(server_id, None)


@dataclass
class Project(Base):
    color: Any = None
    created_at: Any = None
    description: Any = None
    icon: Any = None
    id: Any = None
    name: Any = None
    owner: Any = None
    owner_id: Any = None
    status: Any = None
    tasks: Any = None
    updated_at: Any = None


@dataclass
class Server(Base):
    agent_id: Any = None
    agent_version: Any = None
    cpu_cores: Any = None
    created_at: Any = None
    description: Any = None
    gpu_model: Any = None
    hostname: Any = None
    id: Any = None
    ip_address: Any = None
    last_heartbeat: Any = None
    metrics: Any = None
    name: Any = None
    os_type: Any = None
    port: Any = None
    ram_total_gb: Any = None
    ssh_key_path: Any = None
    ssh_password_encrypted: Any = None
    ssh_username: Any = None
    status: Any = None
    tasks: Any = None
    updated_at: Any = None


@dataclass
class Task(Base):
    assignee: Any = None
    assignee_id: Any = None
    created_at: Any = None
    deadline: Any = None
    description: Any = None
    id: Any = None
    order: Any = None
    priority: Any = None
    project: Any = None
    project_id: Any = None
    server: Any = None
    server_id: Any = None
    status: Any = None
    tags: Any = None
    title: Any = None
    updated_at: Any = None


@dataclass
class User(Base):
    avatar_url: Any = None
    created_at: Any = None
    email: Any = None
    full_name: Any = None
    hashed_password: Any = None
    id: Any = None
    is_active: Any = None
    projects: Any = None
    role: Any = None
    tasks: Any = None
    updated_at: Any = None
    username: Any = None


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
class ProjectStatus:
    name: Any = None


@dataclass
class ServerStatus:
    name: Any = None


@dataclass
class ServerType:
    name: Any = None


@dataclass
class TaskPriority:
    name: Any = None


@dataclass
class TaskStatus:
    name: Any = None


@dataclass
class UserRole:
    name: Any = None


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
    email: Any
    full_name: Optional[str]
    password: str
    username: str


@dataclass
class UserUpdate:
    avatar_url: Optional[str] = None
    email: Optional[Any] = None
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