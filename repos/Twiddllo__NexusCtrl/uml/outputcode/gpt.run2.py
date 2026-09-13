from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union


class WebSocket:
    def __init__(self) -> None:
        self.sent: List[Any] = []

    def send_json(self, data: dict) -> None:
        self.sent.append(data)


class Base:
    def __init__(self) -> None:
        pass


class UserRole:
    def __init__(self, name: str) -> None:
        self.name = name


class ProjectStatus:
    def __init__(self, name: str) -> None:
        self.name = name


class ServerStatus:
    def __init__(self, name: str) -> None:
        self.name = name


class ServerType:
    def __init__(self, name: str) -> None:
        self.name = name


class TaskPriority:
    def __init__(self, name: str) -> None:
        self.name = name


class TaskStatus:
    def __init__(self, name: str) -> None:
        self.name = name


class AuditLog(Base):
    def __init__(
        self,
        action: Any = None,
        details: Any = None,
        id: Any = None,
        ip_address: Any = None,
        resource_id: Any = None,
        resource_type: Any = None,
        timestamp: Any = None,
        user_id: Any = None,
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
        role: Any = None,
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
        self.role = role
        self.updated_at = updated_at
        self.username = username
        self.projects: List[Project] = []
        self.tasks: List[Task] = []


class Project(Base):
    def __init__(
        self,
        color: Any = None,
        created_at: Any = None,
        description: Any = None,
        icon: Any = None,
        id: Any = None,
        name: Any = None,
        owner_id: Any = None,
        status: Any = None,
        updated_at: Any = None,
        owner: Optional[User] = None,
    ) -> None:
        super().__init__()
        self.color = color
        self.created_at = created_at
        self.description = description
        self.icon = icon
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.status = status
        self.updated_at = updated_at
        self.owner: Optional[User] = None
        self.tasks: List[Task] = []
        if owner is not None:
            self.set_owner(owner)

    def set_owner(self, owner: User) -> None:
        self.owner = owner
        self.owner_id = owner.id
        if self not in owner.projects:
            owner.projects.append(self)


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
        name: Any = None,
        os_type: Any = None,
        port: Any = None,
        ram_total_gb: Any = None,
        ssh_key_path: Any = None,
        ssh_password_encrypted: Any = None,
        ssh_username: Any = None,
        status: Any = None,
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
        self.name = name
        self.os_type = os_type
        self.port = port
        self.ram_total_gb = ram_total_gb
        self.ssh_key_path = ssh_key_path
        self.ssh_password_encrypted = ssh_password_encrypted
        self.ssh_username = ssh_username
        self.status = status
        self.updated_at = updated_at
        self.metrics: List[MetricSnapshot] = []
        self.tasks: List[Task] = []


class Task(Base):
    def __init__(
        self,
        assignee_id: Any = None,
        created_at: Any = None,
        deadline: Any = None,
        description: Any = None,
        id: Any = None,
        order: Any = None,
        priority: Any = None,
        project_id: Any = None,
        server_id: Any = None,
        status: Any = None,
        tags: Any = None,
        title: Any = None,
        updated_at: Any = None,
        assignee: Optional[User] = None,
        project: Optional[Project] = None,
        server: Optional[Server] = None,
    ) -> None:
        super().__init__()
        self.assignee_id = assignee_id
        self.created_at = created_at
        self.deadline = deadline
        self.description = description
        self.id = id
        self.order = order
        self.priority = priority
        self.project_id = project_id
        self.server_id = server_id
        self.status = status
        self.tags = tags
        self.title = title
        self.updated_at = updated_at
        self.assignee: Optional[User] = None
        self.project: Optional[Project] = None
        self.server: Optional[Server] = None

        if assignee is not None:
            self.set_assignee(assignee)
        if project is not None:
            self.set_project(project)
        if server is not None:
            self.set_server(server)

    def set_assignee(self, user: User) -> None:
        self.assignee = user
        self.assignee_id = user.id
        if self not in user.tasks:
            user.tasks.append(self)

    def set_project(self, project: Project) -> None:
        self.project = project
        self.project_id = project.id
        if self not in project.tasks:
            project.tasks.append(self)

    def set_server(self, server: Server) -> None:
        self.server = server
        self.server_id = server.id
        if self not in server.tasks:
            server.tasks.append(self)


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
        server_id: Any = None,
        timestamp: Any = None,
        upload_speed_mbps: Any = None,
        server: Optional[Server] = None,
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
        self.server_id = server_id
        self.timestamp = timestamp
        self.upload_speed_mbps = upload_speed_mbps
        self.server: Optional[Server] = None
        if server is not None:
            self.set_server(server)

    def set_server(self, server: Server) -> None:
        self.server = server
        self.server_id = server.id
        if self not in server.metrics:
            server.metrics.append(self)


class MetricsConnectionManager:
    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        self.agent_connections[server_id] = websocket

    def disconnect_agent(self, server_id: int) -> None:
        self.agent_connections.pop(server_id, None)

    def connect_client(self, websocket: WebSocket, server_id: int) -> None:
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        conns = self.client_connections.get(server_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self.client_connections.pop(server_id, None)

    def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        conns = self.client_connections.get(server_id, set())
        for ws in list(conns):
            ws.send_json(data)


class DashboardStats:
    def __init__(
        self,
        active_projects: int,
        completed_tasks: int,
        online_servers: int,
        pending_tasks: int,
        total_projects: int,
        total_servers: int,
        total_tasks: int,
    ) -> None:
        self.active_projects = active_projects
        self.completed_tasks = completed_tasks
        self.online_servers = online_servers
        self.pending_tasks = pending_tasks
        self.total_projects = total_projects
        self.total_servers = total_servers
        self.total_tasks = total_tasks


class SystemHealth:
    def __init__(self, database: bool, redis: bool, status: str, version: str) -> None:
        self.database = database
        self.redis = redis
        self.status = status
        self.version = version


class Settings:
    class Config:
        def __init__(self, case_sensitive: bool, env_file: str) -> None:
            self.case_sensitive = case_sensitive
            self.env_file = env_file

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
        Config: Optional[Settings.Config] = None,
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
        self.Config = Config if Config is not None else Settings.Config(case_sensitive=True, env_file=".env")


class UserLogin:
    def __init__(self, password: str, username: str) -> None:
        self.password = password
        self.username = username


class UserRegister:
    def __init__(self, email: Any, full_name: Optional[str], password: str, username: str) -> None:
        self.email = email
        self.full_name = full_name
        self.password = password
        self.username = username


class UserUpdate:
    def __init__(self, avatar_url: Optional[str] = None, email: Optional[Any] = None, full_name: Optional[str] = None) -> None:
        self.avatar_url = avatar_url
        self.email = email
        self.full_name = full_name


class UserResponse:
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes = from_attributes

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
        Config: Optional[UserResponse.Config] = None,
    ) -> None:
        self.avatar_url = avatar_url
        self.created_at = created_at
        self.email = email
        self.full_name = full_name
        self.id = id
        self.is_active = is_active
        self.role = role
        self.username = username
        self.Config = Config if Config is not None else UserResponse.Config(from_attributes=True)


class TokenRefresh:
    def __init__(self, refresh_token: str) -> None:
        self.refresh_token = refresh_token


class TokenResponse:
    def __init__(self, access_token: str, refresh_token: str, token_type: str, user: UserResponse) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.user = user


class ProjectCreate:
    def __init__(self, color: str, description: Optional[str], icon: str, name: str) -> None:
        self.color = color
        self.description = description
        self.icon = icon
        self.name = name


class ProjectUpdate:
    def __init__(
        self,
        color: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> None:
        self.color = color
        self.description = description
        self.icon = icon
        self.name = name
        self.status = status


class ProjectResponse:
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes = from_attributes

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
        Config: Optional[ProjectResponse.Config] = None,
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
        self.Config = Config if Config is not None else ProjectResponse.Config(from_attributes=True)


class ServerCreate:
    def __init__(
        self,
        description: Optional[str],
        hostname: str,
        ip_address: Optional[str],
        name: str,
        os_type: str,
        port: int,
        ssh_key_path: Optional[str],
        ssh_username: Optional[str],
    ) -> None:
        self.description = description
        self.hostname = hostname
        self.ip_address = ip_address
        self.name = name
        self.os_type = os_type
        self.port = port
        self.ssh_key_path = ssh_key_path
        self.ssh_username = ssh_username


class ServerUpdate:
    def __init__(
        self,
        description: Optional[str] = None,
        hostname: Optional[str] = None,
        ip_address: Optional[str] = None,
        name: Optional[str] = None,
        os_type: Optional[str] = None,
        port: Optional[int] = None,
        ssh_key_path: Optional[str] = None,
        ssh_username: Optional[str] = None,
        status: Optional[str] = None,
    ) -> None:
        self.description = description
        self.hostname = hostname
        self.ip_address = ip_address
        self.name = name
        self.os_type = os_type
        self.port = port
        self.ssh_key_path = ssh_key_path
        self.ssh_username = ssh_username
        self.status = status


class ServerResponse:
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes = from_attributes

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
        Config: Optional[ServerResponse.Config] = None,
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
        self.Config = Config if Config is not None else ServerResponse.Config(from_attributes=True)


class TaskBase:
    def __init__(
        self,
        description: Optional[str],
        due_date: Optional[datetime],
        priority: Any,
        project_id: Optional[int],
        server_id: Optional[int],
        status: Any,
        tags: List[str],
        title: str,
    ) -> None:
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.project_id = project_id
        self.server_id = server_id
        self.status = status
        self.tags = tags
        self.title = title


class TaskCreate(TaskBase):
    def __init__(
        self,
        description: Optional[str],
        due_date: Optional[datetime],
        priority: Any,
        project_id: Optional[int],
        server_id: Optional[int],
        status: Any,
        tags: List[str],
        title: str,
        assignee_id: Optional[int],
    ) -> None:
        super().__init__(
            description=description,
            due_date=due_date,
            priority=priority,
            project_id=project_id,
            server_id=server_id,
            status=status,
            tags=tags,
            title=title,
        )
        self.assignee_id = assignee_id


class TaskUpdate:
    def __init__(
        self,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        position: Optional[int] = None,
        priority: Optional[TaskPriority] = None,
        project_id: Optional[int] = None,
        server_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
    ) -> None:
        self.description = description
        self.due_date = due_date
        self.position = position
        self.priority = priority
        self.project_id = project_id
        self.server_id = server_id
        self.status = status
        self.tags = tags
        self.title = title


class TaskReorder:
    def __init__(self, new_order: int, new_status: str, task_id: int) -> None:
        self.new_order = new_order
        self.new_status = new_status
        self.task_id = task_id


class TaskResponse(TaskBase):
    class Config:
        def __init__(self, from_attributes: bool) -> None:
            self.from_attributes = from_attributes

    def __init__(
        self,
        description: Optional[str],
        due_date: Optional[datetime],
        priority: Any,
        project_id: Optional[int],
        server_id: Optional[int],
        status: Any,
        tags: List[str],
        title: str,
        assignee_id: Optional[int],
        created_at: datetime,
        id: int,
        order: int,
        updated_at: datetime,
        Config: Optional[TaskResponse.Config] = None,
    ) -> None:
        super().__init__(
            description=description,
            due_date=due_date,
            priority=priority,
            project_id=project_id,
            server_id=server_id,
            status=status,
            tags=tags,
            title=title,
        )
        self.assignee_id = assignee_id
        self.created_at = created_at
        self.id = id
        self.order = order
        self.updated_at = updated_at
        self.Config = Config if Config is not None else TaskResponse.Config(from_attributes=True)