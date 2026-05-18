from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, List, Optional, Set, Any


EmailStr = str


class Base:
    _id_counter: int = 1

    def __init__(self, id: Optional[int] = None) -> None:
        if id is None:
            self.id = Base._id_counter
            Base._id_counter += 1
        else:
            self.id = id


class ProjectStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"

    @property
    def name(self) -> str:
        return self.value


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

    @property
    def name(self) -> str:
        return self.value


class ServerType(Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"

    @property
    def name(self) -> str:
        return self.value


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @property
    def name(self) -> str:
        return self.value


class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"

    @property
    def name(self) -> str:
        return self.value


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"

    @property
    def name(self) -> str:
        return self.value


class AuditLog(Base):
    def __init__(
        self,
        action: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        user_id: Optional[int] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id)
        self.action = action
        self.details = details
        self.ip_address = ip_address
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.timestamp = timestamp or datetime.utcnow()
        self.user_id = user_id


class User(Base):
    def __init__(
        self,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_active: bool = True,
        role: str = UserRole.USER.value,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id)
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.avatar_url = avatar_url
        self.is_active = is_active
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.projects: List[Project] = []
        self.tasks: List[Task] = []


class Project(Base):
    def __init__(
        self,
        name: str,
        owner: Optional[User] = None,
        owner_id: Optional[int] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        status: str = ProjectStatus.ACTIVE.value,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id)
        self.name = name
        self.owner = owner
        self.owner_id = owner_id if owner_id is not None else (owner.id if owner else None)
        self.description = description
        self.color = color
        self.icon = icon
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.tasks: List[Task] = []
        if owner is not None:
            owner.projects.append(self)


class Server(Base):
    def __init__(
        self,
        name: str,
        hostname: str,
        os_type: str,
        port: int,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        ssh_username: Optional[str] = None,
        ssh_password_encrypted: Optional[str] = None,
        status: str = ServerStatus.OFFLINE.value,
        agent_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        cpu_cores: Optional[int] = None,
        gpu_model: Optional[str] = None,
        ram_total_gb: Optional[int] = None,
        last_heartbeat: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id)
        self.name = name
        self.hostname = hostname
        self.os_type = os_type
        self.port = port
        self.description = description
        self.ip_address = ip_address
        self.ssh_key_path = ssh_key_path
        self.ssh_username = ssh_username
        self.ssh_password_encrypted = ssh_password_encrypted
        self.status = status
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.cpu_cores = cpu_cores
        self.gpu_model = gpu_model
        self.ram_total_gb = ram_total_gb
        self.last_heartbeat = last_heartbeat
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        self.metrics: List[MetricSnapshot] = []
        self.tasks: List[Task] = []


class Task(Base):
    def __init__(
        self,
        title: str,
        priority: TaskPriority | str,
        status: TaskStatus | str,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None,
        order: int = 0,
        tags: Optional[List[str]] = None,
        assignee: Optional[User] = None,
        assignee_id: Optional[int] = None,
        project: Optional[Project] = None,
        project_id: Optional[int] = None,
        server: Optional[Server] = None,
        server_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id)
        self.title = title
        self.description = description
        self.deadline = deadline
        self.order = order
        self.priority = priority.value if isinstance(priority, TaskPriority) else priority
        self.status = status.value if isinstance(status, TaskStatus) else status
        self.tags = list(tags) if tags is not None else []
        self.assignee = assignee
        self.assignee_id = assignee_id if assignee_id is not None else (assignee.id if assignee else None)
        self.project = project
        self.project_id = project_id if project_id is not None else (project.id if project else None)
        self.server = server
        self.server_id = server_id if server_id is not None else (server.id if server else None)
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at
        if assignee is not None:
            assignee.tasks.append(self)
        if project is not None:
            project.tasks.append(self)
        if server is not None:
            server.tasks.append(self)


class MetricSnapshot(Base):
    def __init__(
        self,
        server: Optional[Server] = None,
        server_id: Optional[int] = None,
        timestamp: Optional[datetime] = None,
        cpu_per_core: Optional[Any] = None,
        cpu_percent: Optional[Any] = None,
        disk_percent: Optional[Any] = None,
        disk_read_mb: Optional[Any] = None,
        disk_write_mb: Optional[Any] = None,
        download_speed_mbps: Optional[Any] = None,
        gpu_memory_percent: Optional[Any] = None,
        gpu_memory_used_mb: Optional[Any] = None,
        gpu_percent: Optional[Any] = None,
        gpu_processes: Optional[Any] = None,
        gpu_temperature: Optional[Any] = None,
        net_connections: Optional[Any] = None,
        net_recv_mb: Optional[Any] = None,
        net_sent_mb: Optional[Any] = None,
        ping_ms: Optional[Any] = None,
        ram_percent: Optional[Any] = None,
        ram_total_gb: Optional[Any] = None,
        ram_used_gb: Optional[Any] = None,
        upload_speed_mbps: Optional[Any] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id)
        self.server = server
        self.server_id = server_id if server_id is not None else (server.id if server else None)
        self.timestamp = timestamp or datetime.utcnow()
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
        self.net_connections = net_connections
        self.net_recv_mb = net_recv_mb
        self.net_sent_mb = net_sent_mb
        self.ping_ms = ping_ms
        self.ram_percent = ram_percent
        self.ram_total_gb = ram_total_gb
        self.ram_used_gb = ram_used_gb
        self.upload_speed_mbps = upload_speed_mbps
        if server is not None:
            server.metrics.append(self)


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


class Settings:
    class Config:
        case_sensitive: bool = True
        env_file: str = ".env"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AGENT_SECRET: str = "agent-secret"
    ALGORITHM: str = "HS256"
    API_PREFIX: str = "/api"
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: List[str] = []
    DATABASE_URL: str = "sqlite:///./app.db"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379/0"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECRET_KEY: str = "secret-key"
    SSH_KEY_PATH: str = "~/.ssh/id_rsa"

    def __init__(
        self,
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 30,
        AGENT_SECRET: str = "agent-secret",
        ALGORITHM: str = "HS256",
        API_PREFIX: str = "/api",
        APP_NAME: str = "NexusCtrl",
        APP_VERSION: str = "1.0.0",
        CORS_ORIGINS: Optional[List[str]] = None,
        DATABASE_URL: str = "sqlite:///./app.db",
        DEBUG: bool = False,
        HOST: str = "127.0.0.1",
        PORT: int = 8000,
        REDIS_URL: str = "redis://localhost:6379/0",
        REFRESH_TOKEN_EXPIRE_DAYS: int = 7,
        SECRET_KEY: str = "secret-key",
        SSH_KEY_PATH: str = "~/.ssh/id_rsa",
    ) -> None:
        self.ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
        self.AGENT_SECRET = AGENT_SECRET
        self.ALGORITHM = ALGORITHM
        self.API_PREFIX = API_PREFIX
        self.APP_NAME = APP_NAME
        self.APP_VERSION = APP_VERSION
        self.CORS_ORIGINS = CORS_ORIGINS or []
        self.DATABASE_URL = DATABASE_URL
        self.DEBUG = DEBUG
        self.HOST = HOST
        self.PORT = PORT
        self.REDIS_URL = REDIS_URL
        self.REFRESH_TOKEN_EXPIRE_DAYS = REFRESH_TOKEN_EXPIRE_DAYS
        self.SECRET_KEY = SECRET_KEY
        self.SSH_KEY_PATH = SSH_KEY_PATH


@dataclass
class ProjectCreate:
    color: str
    description: Optional[str]
    icon: str
    name: str


class ProjectResponse:
    class Config:
        from_attributes: bool = True

    def __init__(
        self,
        color: str,
        completed_tasks: int,
        created_at: Optional[datetime],
        description: Optional[str],
        icon: str,
        id: int,
        name: str,
        owner_id: int,
        status: str,
        task_count: int,
        updated_at: Optional[datetime],
    ) -> None:
        self.color = color
        self.completed_tasks = completed_tasks
        self.created_at = created_at
        self.description = description
        self.icon = icon
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.status = status
        self.task_count = task_count
        self.updated_at = updated_at


@dataclass
class ProjectUpdate:
    color: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


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


class ServerResponse:
    class Config:
        from_attributes: bool = True

    def __init__(
        self,
        agent_id: Optional[str],
        agent_version: Optional[str],
        cpu_cores: Optional[int],
        created_at: Optional[datetime],
        description: Optional[str],
        gpu_model: Optional[str],
        hostname: str,
        id: int,
        ip_address: Optional[str],
        last_heartbeat: Optional[datetime],
        name: str,
        os_type: str,
        port: int,
        ram_total_gb: Optional[int],
        ssh_username: Optional[str],
        status: str,
        task_count: int,
        updated_at: Optional[datetime],
    ) -> None:
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
        self.name = name
        self.os_type = os_type
        self.port = port
        self.ram_total_gb = ram_total_gb
        self.ssh_username = ssh_username
        self.status = status
        self.task_count = task_count
        self.updated_at = updated_at


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
class TaskBase:
    title: str
    priority: TaskPriority | str
    status: TaskStatus | str
    tags: List[str]
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None


@dataclass
class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskResponse(TaskBase):
    class Config:
        from_attributes: bool = True

    def __init__(
        self,
        title: str,
        priority: TaskPriority | str,
        status: TaskStatus | str,
        tags: List[str],
        created_at: datetime,
        id: int,
        order: int,
        updated_at: datetime,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        project_id: Optional[int] = None,
        server_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
    ) -> None:
        super().__init__(
            title=title,
            priority=priority,
            status=status,
            tags=tags,
            description=description,
            due_date=due_date,
            project_id=project_id,
            server_id=server_id,
        )
        self.assignee_id = assignee_id
        self.created_at = created_at
        self.id = id
        self.order = order
        self.updated_at = updated_at


@dataclass
class TaskReorder:
    new_order: int
    new_status: str
    task_id: int


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
class TokenRefresh:
    refresh_token: str


class UserResponse:
    class Config:
        from_attributes: bool = True

    def __init__(
        self,
        avatar_url: Optional[str],
        created_at: Optional[datetime],
        email: str,
        full_name: Optional[str],
        id: int,
        is_active: bool,
        role: str,
        username: str,
    ) -> None:
        self.avatar_url = avatar_url
        self.created_at = created_at
        self.email = email
        self.full_name = full_name
        self.id = id
        self.is_active = is_active
        self.role = role
        self.username = username


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


@dataclass
class UserLogin:
    password: str
    username: str


@dataclass
class UserRegister:
    email: Annotated[EmailStr, "EmailStr"]
    full_name: Optional[str]
    password: str
    username: str


@dataclass
class UserUpdate:
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class WebSocket:
    def __init__(self) -> None:
        self.sent_messages: List[Any] = []

    async def send_json(self, data: dict) -> None:
        self.sent_messages.append(data)


class MetricsConnectionManager:
    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        self.agent_connections[server_id] = websocket

    def connect_client(self, websocket: WebSocket, server_id: int) -> None:
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
        for websocket in self.client_connections.get(server_id, set()):
            await websocket.send_json(data)