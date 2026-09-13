from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union


class WebSocket:
    async def accept(self) -> None:
        raise NotImplementedError

    async def send_json(self, data: dict) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class Base:
    def __init__(self) -> None:
        pass


class Settings:
    class Config:
        def __init__(self, case_sensitive: bool, env_file: str) -> None:
            self.case_sensitive: bool = case_sensitive
            self.env_file: str = env_file

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
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = ACCESS_TOKEN_EXPIRE_MINUTES
        self.AGENT_SECRET: str = AGENT_SECRET
        self.ALGORITHM: str = ALGORITHM
        self.API_PREFIX: str = API_PREFIX
        self.APP_NAME: str = APP_NAME
        self.APP_VERSION: str = APP_VERSION
        self.CORS_ORIGINS: List[str] = list(CORS_ORIGINS)
        self.DATABASE_URL: str = DATABASE_URL
        self.DEBUG: bool = DEBUG
        self.HOST: str = HOST
        self.PORT: int = PORT
        self.REDIS_URL: str = REDIS_URL
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = REFRESH_TOKEN_EXPIRE_DAYS
        self.SECRET_KEY: str = SECRET_KEY
        self.SSH_KEY_PATH: str = SSH_KEY_PATH


@dataclass(frozen=True)
class ProjectStatus:
    name: str


@dataclass(frozen=True)
class ServerStatus:
    name: str


@dataclass(frozen=True)
class ServerType:
    name: str


@dataclass(frozen=True)
class TaskPriority:
    name: str


@dataclass(frozen=True)
class TaskStatus:
    name: str


@dataclass(frozen=True)
class UserRole:
    name: str


class AuditLog(Base):
    def __init__(
        self,
        action: Any,
        details: Any,
        id: Any,
        ip_address: Any,
        resource_id: Any,
        resource_type: Any,
        timestamp: Any,
        user_id: Any,
    ) -> None:
        super().__init__()
        self.action = action
        self.details = details
        self.id = id
        self.ip_address = ip_address
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.timestamp = timestamp
        self.user_id = user_id


class User(Base):
    def __init__(
        self,
        avatar_url: Any = None,
        created_at: Any = None,
        email: Any = None,
        full_name: Any = None,
        hashed_password: Any = None,
        id: Any = None,
        is_active: Any = None,
        projects: Any = None,
        role: Any = None,
        tasks: Any = None,
        updated_at: Any = None,
        username: Any = None,
    ) -> None:
        super().__init__()
        self.avatar_url = avatar_url
        self.created_at = created_at
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.id = id
        self.is_active = is_active
        self.projects = projects
        self.role = role
        self.tasks = tasks
        self.updated_at = updated_at
        self.username = username


class Project(Base):
    def __init__(
        self,
        color: Any = None,
        created_at: Any = None,
        description: Any = None,
        icon: Any = None,
        id: Any = None,
        name: Any = None,
        owner: Any = None,
        owner_id: Any = None,
        status: Any = None,
        tasks: Any = None,
        updated_at: Any = None,
    ) -> None:
        super().__init__()
        self.color = color
        self.created_at = created_at
        self.description = description
        self.icon = icon
        self.id = id
        self.name = name
        self.owner = owner
        self.owner_id = owner_id
        self.status = status
        self.tasks = tasks
        self.updated_at = updated_at


class Server(Base):
    def __init__(
        self,
        agent_id: Any = None,
        agent_version: Any = None,
        cpu_cores: Any = None,
        created_at: Any = None,
        description: Any = None,
        gpu_model: Any = None,
        hostname: Any = None,
        id: Any = None,
        ip_address: Any = None,
        last_heartbeat: Any = None,
        metrics: Any = None,
        name: Any = None,
        os_type: Any = None,
        port: Any = None,
        ram_total_gb: Any = None,
        ssh_key_path: Any = None,
        ssh_password_encrypted: Any = None,
        ssh_username: Any = None,
        status: Any = None,
        tasks: Any = None,
        updated_at: Any = None,
    ) -> None:
        super().__init__()
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.cpu_cores = cpu_cores
        self.created_at = created_at
        self.description = description
        self.gpu_model = gpu_model
        self.hostname = hostname
        self.id = id
        self.ip_address = ip_address
        self.last_heartbeat = last_heartbeat
        self.metrics = metrics
        self.name = name
        self.os_type = os_type
        self.port = port
        self.ram_total_gb = ram_total_gb
        self.ssh_key_path = ssh_key_path
        self.ssh_password_encrypted = ssh_password_encrypted
        self.ssh_username = ssh_username
        self.status = status
        self.tasks = tasks
        self.updated_at = updated_at


class Task(Base):
    def __init__(
        self,
        assignee: Any = None,
        assignee_id: Any = None,
        created_at: Any = None,
        deadline: Any = None,
        description: Any = None,
        id: Any = None,
        order: Any = None,
        priority: Any = None,
        project: Any = None,
        project_id: Any = None,
        server: Any = None,
        server_id: Any = None,
        status: Any = None,
        tags: Any = None,
        title: Any = None,
        updated_at: Any = None,
    ) -> None:
        super().__init__()
        self.assignee = assignee
        self.assignee_id = assignee_id
        self.created_at = created_at
        self.deadline = deadline
        self.description = description
        self.id = id
        self.order = order
        self.priority = priority
        self.project = project
        self.project_id = project_id
        self.server = server
        self.server_id = server_id
        self.status = status
        self.tags = tags
        self.title = title
        self.updated_at = updated_at


class MetricSnapshot(Base):
    def __init__(
        self,
        cpu_per_core: Any = None,
        cpu_percent: Any = None,
        disk_percent: Any = None,
        disk_read_mb: Any = None,
        disk_write_mb: Any = None,
        download_speed_mbps: Any = None,
        gpu_memory_percent: Any = None,
        gpu_memory_used_mb: Any = None,
        gpu_percent: Any = None,
        gpu_processes: Any = None,
        gpu_temperature: Any = None,
        id: Any = None,
        net_connections: Any = None,
        net_recv_mb: Any = None,
        net_sent_mb: Any = None,
        ping_ms: Any = None,
        ram_percent: Any = None,
        ram_total_gb: Any = None,
        ram_used_gb: Any = None,
        server: Any = None,
        server_id: Any = None,
        timestamp: Any = None,
        upload_speed_mbps: Any = None,
    ) -> None:
        super().__init__()
        self.cpu_per_core = cpu_per_core
        self.cpu_percent = cpu_percent
        self.disk_percent = disk_percent
        self.disk_read_mb = disk_read_mb
        self.disk_write_mb = disk_write_mb
        self.download_speed_mbps = download_speed_mbps
        self.gpu_memory_percent = gpu_memory_percent
        self.gpu_memory_used_mb = gpu_memory_used_mb
        self.gpu_percent = gpu_percent
        self.gpu_processes = gpu_processes
        self.gpu_temperature = gpu_temperature
        self.id = id
        self.net_connections = net_connections
        self.net_recv_mb = net_recv_mb
        self.net_sent_mb = net_sent_mb
        self.ping_ms = ping_ms
        self.ram_percent = ram_percent
        self.ram_total_gb = ram_total_gb
        self.ram_used_gb = ram_used_gb
        self.server = server
        self.server_id = server_id
        self.timestamp = timestamp
        self.upload_speed_mbps = upload_speed_mbps


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
        conns = self.client_connections.get(server_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        conns = self.client_connections.get(server_id)
        if not conns:
            return
        for ws in list(conns):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect_client(ws, server_id)


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
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes: bool = from_attributes

    avatar_url: Optional[str]
    created_at: Optional[datetime]
    email: str
    full_name: Optional[str]
    id: int
    is_active: bool
    role: str
    username: str


@dataclass
class TokenRefresh:
    refresh_token: str


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


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
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes: bool = from_attributes

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
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes: bool = from_attributes

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


@dataclass
class TaskBase:
    description: Optional[str]
    due_date: Optional[datetime]
    priority: TaskPriority
    project_id: Optional[int]
    server_id: Optional[int]
    status: TaskStatus
    tags: List[str]
    title: str


@dataclass
class TaskCreate(TaskBase):
    assignee_id: Optional[int]


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
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes: bool = from_attributes

    assignee_id: Optional[int]
    created_at: datetime
    id: int
    order: int
    updated_at: datetime