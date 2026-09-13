import os
import sys
import time
import json
import socket
import struct
import threading
import subprocess
import base64
import io
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

try:
    import psutil
except ImportError:
    psutil = None

try:
    from PIL import ImageGrab, Image
except ImportError:
    ImageGrab = None
    Image = None

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    HAS_TK = True
except ImportError:
    HAS_TK = False


# ─────────────────────────────────────────────
# Enums & Data Classes
# ─────────────────────────────────────────────

class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ERROR = "error"


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    username: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "status": self.status,
            "username": self.username,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProcessInfo":
        return cls(
            pid=d.get("pid", 0),
            name=d.get("name", ""),
            cpu_percent=d.get("cpu_percent", 0.0),
            memory_mb=d.get("memory_mb", 0.0),
            status=d.get("status", ""),
            username=d.get("username", ""),
        )


@dataclass
class SystemMetrics:
    timestamp: float
    cpu_percent: float
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float
    net_bytes_sent: int
    net_bytes_recv: int
    processes: List[ProcessInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "net_bytes_sent": self.net_bytes_sent,
            "net_bytes_recv": self.net_bytes_recv,
            "processes": [p.to_dict() for p in self.processes],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SystemMetrics":
        procs = [ProcessInfo.from_dict(p) for p in d.get("processes", [])]
        return cls(
            timestamp=d.get("timestamp", 0.0),
            cpu_percent=d.get("cpu_percent", 0.0),
            ram_percent=d.get("ram_percent", 0.0),
            ram_used_mb=d.get("ram_used_mb", 0.0),
            ram_total_mb=d.get("ram_total_mb", 0.0),
            net_bytes_sent=d.get("net_bytes_sent", 0),
            net_bytes_recv=d.get("net_bytes_recv", 0),
            processes=procs,
        )


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    server_id: Optional[str]
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "server_id": self.server_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        return cls(
            task_id=d["task_id"],
            title=d["title"],
            description=d.get("description", ""),
            priority=TaskPriority(d.get("priority", "medium")),
            status=TaskStatus(d.get("status", "pending")),
            server_id=d.get("server_id"),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
            completed_at=d.get("completed_at"),
        )


@dataclass
class ServerConfig:
    server_id: str
    name: str
    host: str
    port: int
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ServerConfig":
        return cls(
            server_id=d["server_id"],
            name=d["name"],
            host=d["host"],
            port=d["port"],
            description=d.get("description", ""),
        )


# ─────────────────────────────────────────────
# Protocol helpers
# ─────────────────────────────────────────────

def send_message(sock: socket.socket, data: Dict[str, Any]) -> None:
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack(">I", len(payload))
    sock.sendall(header + payload)


def recv_message(sock: socket.socket) -> Optional[Dict[str, Any]]:
    try:
        raw_len = _recv_exact(sock, 4)
        if raw_len is None:
            return None
        msg_len = struct.unpack(">I", raw_len)[0]
        raw_data = _recv_exact(sock, msg_len)
        if raw_data is None:
            return None
        return json.loads(raw_data.decode("utf-8"))
    except Exception:
        return None


def _recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
    data = b""
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
        except Exception:
            return None
        if not chunk:
            return None
        data += chunk
    return data


# ─────────────────────────────────────────────
# Agent (runs on target machine)
# ─────────────────────────────────────────────

class Agent:
    """Runs as a background service on target machines."""

    COLLECT_INTERVAL = 2  # seconds

    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._metrics_lock = threading.Lock()
        self._latest_metrics: Optional[SystemMetrics] = None
        self._history: deque = deque(maxlen=300)  # ~10 min at 2s interval
        self._collector_thread: Optional[threading.Thread] = None

    # ── metric collection ──────────────────────────────────────────────

    def _collect_metrics(self) -> SystemMetrics:
        if psutil is None:
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                ram_percent=0.0,
                ram_used_mb=0.0,
                ram_total_mb=0.0,
                net_bytes_sent=0,
                net_bytes_recv=0,
            )

        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        net = psutil.net_io_counters()

        processes: List[ProcessInfo] = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_info", "status", "username"]
        ):
            try:
                info = proc.info
                mem_mb = (
                    info["memory_info"].rss / (1024 * 1024)
                    if info.get("memory_info")
                    else 0.0
                )
                processes.append(
                    ProcessInfo(
                        pid=info["pid"],
                        name=info.get("name", ""),
                        cpu_percent=info.get("cpu_percent", 0.0) or 0.0,
                        memory_mb=mem_mb,
                        status=info.get("status", ""),
                        username=info.get("username", "") or "",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=cpu,
            ram_percent=vm.percent,
            ram_used_mb=vm.used / (1024 * 1024),
            ram_total_mb=vm.total / (1024 * 1024),
            net_bytes_sent=net.bytes_sent,
            net_bytes_recv=net.bytes_recv,
            processes=processes,
        )

    def _collector_loop(self) -> None:
        if psutil:
            psutil.cpu_percent(interval=None)  # prime
        while self._running:
            metrics = self._collect_metrics()
            with self._metrics_lock:
                self._latest_metrics = metrics
                self._history.append(metrics)
            time.sleep(self.COLLECT_INTERVAL)

    # ── screen capture ─────────────────────────────────────────────────

    def _capture_screen(self) -> Optional[str]:
        if ImageGrab is None:
            return None
        try:
            img = ImageGrab.grab()
            img.thumbnail((1280, 720), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

    # ── process control ────────────────────────────────────────────────

    def _kill_process(self, pid: int) -> Tuple[bool, str]:
        if psutil is None:
            return False, "psutil not available"
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            return True, f"Process {pid} terminated"
        except psutil.NoSuchProcess:
            return False, f"Process {pid} not found"
        except psutil.AccessDenied:
            return False, f"Access denied for process {pid}"
        except Exception as e:
            return False, str(e)

    # ── client handler ─────────────────────────────────────────────────

    def _handle_client(self, conn: socket.socket, addr: Tuple) -> None:
        conn.settimeout(30)
        try:
            while self._running:
                msg = recv_message(conn)
                if msg is None:
                    break
                cmd = msg.get("cmd", "")
                response: Dict[str, Any] = {"cmd": cmd, "ok": True}

                if cmd == "ping":
                    response["data"] = "pong"

                elif cmd == "get_metrics":
                    with self._metrics_lock:
                        m = self._latest_metrics
                    if m:
                        response["data"] = m.to_dict()
                    else:
                        response["data"] = None

                elif cmd == "get_history":
                    with self._metrics_lock:
                        hist = [m.to_dict() for m in self._history]
                    response["data"] = hist

                elif cmd == "get_screen":
                    img_b64 = self._capture_screen()
                    response["data"] = img_b64

                elif cmd == "kill_process":
                    pid = msg.get("pid")
                    if pid is None:
                        response["ok"] = False
                        response["error"] = "No PID provided"
                    else:
                        ok, msg_str = self._kill_process(int(pid))
                        response["ok"] = ok
                        response["data"] = msg_str

                elif cmd == "get_processes":
                    with self._metrics_lock:
                        m = self._latest_metrics
                    if m:
                        response["data"] = [p.to_dict() for p in m.processes]
                    else:
                        response["data"] = []

                else:
                    response["ok"] = False
                    response["error"] = f"Unknown command: {cmd}"

                send_message(conn, response)
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ── server loop ────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._collector_thread = threading.Thread(
            target=self._collector_loop, daemon=True
        )
        self._collector_thread.start()

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(10)
        self._server_sock.settimeout(1.0)

        print(f"[Agent] Listening on {self.host}:{self.port}")
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                t = threading.Thread(
                    target=self._handle_client, args=(conn, addr), daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def stop(self) -> None:
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass


# ─────────────────────────────────────────────
# ServerConnection (controller side)
# ─────────────────────────────────────────────

class ServerConnection:
    """Manages a persistent connection to one agent."""

    RECONNECT_INTERVAL = 5

    def __init__(self, config: ServerConfig):
        self.config = config
        self.status = ServerStatus.OFFLINE
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._latest_metrics: Optional[SystemMetrics] = None
        self._history: deque = deque(maxlen=300)
        self._latest_screen: Optional[str] = None
        self._callbacks: List[Any] = []
        self._metrics_lock = threading.Lock()

    # ── connection management ──────────────────────────────────────────

    def _connect(self) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.config.host, self.config.port))
            sock.settimeout(10)
            with self._lock:
                self._sock = sock
            self.status = ServerStatus.ONLINE
            return True
        except Exception:
            self.status = ServerStatus.OFFLINE
            return False

    def _disconnect(self) -> None:
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
        self.status = ServerStatus.OFFLINE

    def _send_cmd(self, cmd: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            sock = self._sock
        if sock is None:
            return None
        try:
            send_message(sock, cmd)
            return recv_message(sock)
        except Exception:
            self._disconnect()
            return None

    # ── monitor loop ───────────────────────────────────────────────────

    def _monitor_loop(self) -> None:
        while self._running:
            if self.status != ServerStatus.ONLINE:
                self.status = ServerStatus.CONNECTING
                if not self._connect():
                    time.sleep(self.RECONNECT_INTERVAL)
                    continue

            resp = self._send_cmd({"cmd": "get_metrics"})
            if resp and resp.get("ok") and resp.get("data"):
                m = SystemMetrics.from_dict(resp["data"])
                with self._metrics_lock:
                    self._latest_metrics = m
                    self._history.append(m)
            else:
                self._disconnect()

            time.sleep(2)

    def start_monitoring(self) -> None:
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._running = False
        self._disconnect()

    # ── public API ─────────────────────────────────────────────────────

    def get_metrics(self) -> Optional[SystemMetrics]:
        with self._metrics_lock:
            return self._latest_metrics

    def get_history(self) -> List[SystemMetrics]:
        with self._metrics_lock:
            return list(self._history)

    def get_screen(self) -> Optional[str]:
        resp = self._send_cmd({"cmd": "get_screen"})
        if resp and resp.get("ok"):
            return resp.get("data")
        return None

    def get_processes(self) -> List[ProcessInfo]:
        resp = self._send_cmd({"cmd": "get_processes"})
        if resp and resp.get("ok"):
            return [ProcessInfo.from_dict(p) for p in resp.get("data", [])]
        return []

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        resp = self._send_cmd({"cmd": "kill_process", "pid": pid})
        if resp is None:
            return False, "No response from agent"
        return resp.get("ok", False), resp.get("data", resp.get("error", ""))

    def ping(self) -> bool:
        resp = self._send_cmd({"cmd": "ping"})
        return resp is not None and resp.get("data") == "pong"


# ─────────────────────────────────────────────
# Task Manager
# ─────────────────────────────────────────────

class TaskManager:
    def __init__(self, storage_path: str = "tasks.json"):
        self.storage_path = storage_path
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                for d in data:
                    t = Task.from_dict(d)
                    self._tasks[t.task_id] = t
            except Exception:
                pass

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w") as f:
                json.dump([t.to_dict() for t in self._tasks.values()], f, indent=2)
        except Exception:
            pass

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        server_id: Optional[str] = None,
    ) -> Task:
        task_id = f"task_{int(time.time() * 1000)}_{len(self._tasks)}"
        now = time.time()
        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            status=TaskStatus.PENDING,
            server_id=server_id,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks[task_id] = task
            self._save()
        return task

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        status: Optional[TaskStatus] = None,
        server_id: Optional[str] = None,
    ) -> Optional[Task]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if title is not None:
                task.title = title
            if description is not None:
                task.description = description
            if priority is not None:
                task.priority = priority
            if status is not None:
                task.status = status
                if status == TaskStatus.COMPLETED:
                    task.completed_at = time.time()
            if server_id is not None:
                task.server_id = server_id
            task.updated_at = time.time()
            self._save()
        return task

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._save()
                return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        server_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
    ) -> List[Task]:
        tasks = list(self._tasks.values())
        if server_id is not None:
            tasks = [t for t in tasks if t.server_id == server_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 99), t.created_at))
        return tasks


# ─────────────────────────────────────────────
# Server Manager
# ─────────────────────────────────────────────

class ServerManager:
    def __init__(self, storage_path: str = "servers.json"):
        self.storage_path = storage_path
        self._configs: Dict[str, ServerConfig] = {}
        self._connections: Dict[str, ServerConnection] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                for d in data:
                    cfg = ServerConfig.from_dict(d)
                    self._configs[cfg.server_id] = cfg
            except Exception:
                pass

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w") as f:
                json.dump(
                    [c.to_dict() for c in self._configs.values()], f, indent=2
                )
        except Exception:
            pass

    def add_server(
        self, name: str, host: str, port: int = 9000, description: str = ""
    ) -> ServerConfig:
        server_id = f"srv_{int(time.time() * 1000)}_{len(self._configs)}"
        cfg = ServerConfig(
            server_id=server_id,
            name=name,
            host=host,
            port=port,
            description=description,
        )
        with self._lock:
            self._configs[server_id] = cfg
            self._save()
        return cfg

    def remove_server(self, server_id: str) -> bool:
        with self._lock:
            if server_id in self._connections:
                self._connections[server_id].stop_monitoring()
                del self._connections[server_id]
            if server_id in self._configs:
                del self._configs[server_id]
                self._save()
                return True
        return False

    def update_server(
        self,
        server_id: str,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Optional[ServerConfig]:
        with self._lock:
            cfg = self._configs.get(server_id)
            if cfg is None:
                return None
            if name is not None:
                cfg.name = name
            if host is not None:
                cfg.host = host
            if port is not None:
                cfg.port = port
            if description is not None:
                cfg.description = description
            self._save()
        return cfg

    def list_servers(self) -> List[ServerConfig]:
        return list(self._configs.values())

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        return self._configs.get(server_id)

    def connect(self, server_id: str) -> Optional[ServerConnection]:
        cfg = self._configs.get(server_id)
        if cfg is None:
            return None
        with self._lock:
            if server_id not in self._connections:
                conn = ServerConnection(cfg)
                conn.start_monitoring()
                self._connections[server_id] = conn
        return self._connections[server_id]

    def disconnect(self, server_id: str) -> None:
        with self._lock:
            if server_id in self._connections:
                self._connections[server_id].stop_monitoring()
                del self._connections[server_id]

    def get_connection(self, server_id: str) -> Optional[ServerConnection]:
        return self._connections.get(server_id)

    def connect_all(self) -> None:
        for server_id in list(self._configs.keys()):
            self.connect(server_id)

    def disconnect_all(self) -> None:
        for server_id in list(self._connections.keys()):
            self.disconnect(server_id)


# ─────────────────────────────────────────────
# NexusCtrl Core
# ─────────────────────────────────────────────

class NexusCtrl:
    """Main controller that ties everything together."""

    def __init__(
        self,
        servers_path: str = "nexus_servers.json",
        tasks_path: str = "nexus_tasks.json",
    ):
        self.server_manager = ServerManager(servers_path)
        self.task_manager = TaskManager(tasks_path)

    # ── server operations ──────────────────────────────────────────────

    def add_server(
        self, name: str, host: str, port: int = 9000, description: str = ""
    ) -> ServerConfig:
        return self.server_manager.add_server(name, host, port, description)

    def remove_server(self, server_id: str) -> bool:
        return self.server_manager.remove_server(server_id)

    def list_servers(self) -> List[ServerConfig]:
        return self.server_manager.list_servers()

    def connect_server(self, server_id: str) -> Optional[ServerConnection]:
        return self.server_manager.connect(server_id)

    def connect_all(self) -> None:
        self.server_manager.connect_all()

    def disconnect_all(self) -> None:
        self.server_manager.disconnect_all()

    def get_metrics(self, server_id: str) -> Optional[SystemMetrics]:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.get_metrics()
        return None

    def get_history(self, server_id: str) -> List[SystemMetrics]:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.get_history()
        return []

    def get_screen(self, server_id: str) -> Optional[str]:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.get_screen()
        return None

    def get_processes(self, server_id: str) -> List[ProcessInfo]:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.get_processes()
        return []

    def kill_process(self, server_id: str, pid: int) -> Tuple[bool, str]:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.kill_process(pid)
        return False, "Server not connected"

    def get_server_status(self, server_id: str) -> ServerStatus:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.status
        return ServerStatus.OFFLINE

    # ── task operations ────────────────────────────────────────────────

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        server_id: Optional[str] = None,
    ) -> Task:
        return self.task_manager.create_task(title, description, priority, server_id)

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        return self.task_manager.update_task(task_id, **kwargs)

    def delete_task(self, task_id: str) -> bool:
        return self.task_manager.delete_task(task_id)

    def list_tasks(self, **kwargs) -> List[Task]:
        return self.task_manager.list_tasks(**kwargs)

    def complete_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.update_task(task_id, status=TaskStatus.COMPLETED)

    def cancel_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.update_task(task_id, status=TaskStatus.CANCELLED)


# ─────────────────────────────────────────────
# GUI (Tkinter)
# ─────────────────────────────────────────────

if HAS_TK:

    class NexusGUI:
        STATUS_COLORS = {
            ServerStatus.ONLINE: "#00cc44",
            ServerStatus.OFFLINE: "#cc0000",
            ServerStatus.CONNECTING: "#ff9900",
            ServerStatus.ERROR: "#cc0000",
        }

        def __init__(self, ctrl: NexusCtrl):
            self.ctrl = ctrl
            self.root = tk.Tk()
            self.root.title("NexusCtrl - RDP Server Management")
            self.root.geometry("1200x750")
            self.root.configure(bg="#1e1e2e")
            self._selected_server_id: Optional[str] = None
            self._screen_window: Optional[tk.Toplevel] = None
            self._build_ui()
            self._refresh_server_list()
            self._refresh_task_list()
            self._start_auto_refresh()

        # ── UI build ───────────────────────────────────────────────────

        def _build_ui(self) -> None:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure(
                "TNotebook",
                background="#1e1e2e",
                borderwidth=0,
            )
            style.configure(
                "TNotebook.Tab",
                background="#313244",
                foreground="#cdd6f4",
                padding=[10, 4],
            )
            style.map(
                "TNotebook.Tab",
                background=[("selected", "#89b4fa")],
                foreground=[("selected", "#1e1e2e")],
            )
            style.configure(
                "Treeview",
                background="#313244",
                foreground="#cdd6f4",
                fieldbackground="#313244",
                rowheight=24,
            )
            style.configure(
                "Treeview.Heading",
                background="#45475a",
                foreground="#cdd6f4",
            )
            style.map("Treeview", background=[("selected", "#89b4fa")])

            # Top bar
            top = tk.Frame(self.root, bg="#181825", height=50)
            top.pack(fill=tk.X)
            tk.Label(
                top,
                text="⚡ NexusCtrl",
                bg="#181825",
                fg="#89b4fa",
                font=("Consolas", 16, "bold"),
            ).pack(side=tk.LEFT, padx=15, pady=10)

            self._status_var = tk.StringVar(value="Ready")
            tk.Label(
                top,
                textvariable=self._status_var,
                bg="#181825",
                fg="#a6e3a1",
                font=("Consolas", 10),
            ).pack(side=tk.RIGHT, padx=15)

            # Main notebook
            nb = ttk.Notebook(self.root)
            nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            self._tab_servers = tk.Frame(nb, bg="#1e1e2e")
            self._tab_tasks = tk.Frame(nb, bg="#1e1e2e")
            self._tab_monitor = tk.Frame(nb, bg="#1e1e2e")

            nb.add(self._tab_servers, text="  Servers  ")
            nb.add(self._tab_monitor, text="  Monitor  ")
            nb.add(self._tab_tasks, text="  Tasks  ")

            self._build_servers_tab()
            self._build_monitor_tab()
            self._build_tasks_tab()

        # ── Servers tab ────────────────────────────────────────────────

        def _build_servers_tab(self) -> None:
            tab = self._tab_servers

            # Left: server list
            left = tk.Frame(tab, bg="#1e1e2e", width=350)
            left.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 2), pady=5)
            left.pack_propagate(False)

            tk.Label(
                left, text="Servers", bg="#1e1e2e", fg="#89b4fa",
                font=("Consolas", 12, "bold")
            ).pack(anchor=tk.W, padx=5, pady=(5, 2))

            cols = ("name", "host", "port", "status")
            self._srv_tree = ttk.Treeview(left, columns=cols, show="headings", height=15)
            for c, w in zip(cols, (120, 120, 60, 80)):
                self._srv_tree.heading(c, text=c.capitalize())
                self._srv_tree.column(c, width=w, anchor=tk.W)
            self._srv_tree.pack(fill=tk.BOTH, expand=True, padx=5)
            self._srv_tree.bind("<<TreeviewSelect>>", self._on_server_select)

            btn_frame = tk.Frame(left, bg="#1e1e2e")
            btn_frame.pack(fill=tk.X, padx=5, pady=5)
            self._btn(btn_frame, "Add", self._add_server_dialog).pack(side=tk.LEFT, padx=2)
            self._btn(btn_frame, "Remove", self._remove_server).pack(side=tk.LEFT, padx=2)
            self._btn(btn_frame, "Connect", self._connect_server).pack(side=tk.LEFT, padx=2)
            self._btn(btn_frame, "Disconnect", self._disconnect_server).pack(side=tk.LEFT, padx=2)

            # Right: server detail
            right = tk.Frame(tab, bg="#1e1e2e")
            right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 5), pady=5)

            tk.Label(
                right, text="Server Detail", bg="#1e1e2e", fg="#89b4fa",
                font=("Consolas", 12, "bold")
            ).pack(anchor=tk.W, padx=5, pady=(5, 2))

            self._detail_text = scrolledtext.ScrolledText(
                right, bg="#313244", fg="#cdd6f4", font=("Consolas", 10),
                state=tk.DISABLED, height=10
            )
            self._detail_text.pack(fill=tk.X, padx=5)

            # Processes
            tk.Label(
                right, text="Processes", bg="#1e1e2e", fg="#89b4fa",
                font=("Consolas", 11, "bold")
            ).pack(anchor=tk.W, padx=5, pady=(10, 2))

            proc_cols = ("pid", "name", "cpu", "mem", "status", "user")
            self._proc_tree = ttk.Treeview(
                right, columns=proc_cols, show="headings", height=12
            )
            for c, w in zip(proc_cols, (60, 160, 70, 80, 80, 100)):
                self._proc_tree.heading(c, text=c.upper())
                self._proc_tree.column(c, width=w, anchor=tk.W)
            self._proc_tree.pack(fill=tk.BOTH, expand=True, padx=5)

            proc_btn = tk.Frame(right, bg="#1e1e2e")
            proc_btn.pack(fill=tk.X, padx=5, pady=3)
            self._btn(proc_btn, "Kill Process", self._kill_selected_process).pack(side=tk.LEFT, padx=2)
            self._btn(proc_btn, "Refresh Processes", self._refresh_processes).pack(side=tk.LEFT, padx=2)
            self._btn(proc_btn, "View Screen", self._view_screen).pack(side=tk.LEFT, padx=2)

        # ── Monitor tab ────────────────────────────────────────────────

        def _build_monitor_tab(self) -> None:
            tab = self._tab_monitor

            tk.Label(
                tab, text="Live Metrics", bg="#1e1e2e", fg="#89b4fa",
                font=("Consolas", 12, "bold")
            ).pack(anchor=tk.W, padx=10, pady=(8, 2))

            # Metrics grid
            self._metrics_frame = tk.Frame(tab, bg="#1e1e2e")
            self._metrics_frame.pack(fill=tk.X, padx=10, pady=5)

            self._metric_cards: Dict[str, Dict[str, tk.StringVar]] = {}

            # History log
            tk.Label(
                tab, text="Performance History", bg="#1e1e2e", fg="#89b4fa",
                font=("Consolas", 11, "bold")
            ).pack(anchor=tk.W, padx=10, pady=(10, 2))

            self._history_text = scrolledtext.ScrolledText(
                tab, bg="#313244", fg="#cdd6f4", font=("Consolas", 9),
                state=tk.DISABLED, height=15
            )
            self._history_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

            self._btn(tab, "Refresh All", self._refresh_all_metrics).pack(
                anchor=tk.W, padx=10, pady=3
            )

        # ── Tasks tab ─────────────────────────────────────────────────

        def _build_tasks_tab(self) -> None:
            tab = self._tab_tasks

            top = tk.Frame(tab, bg="#1e1e2e")
            top.pack(fill=tk.X, padx=10, pady=5)

            tk.Label(
                top, text="Tasks", bg="#1e1e2e", fg="#89b4fa",
                font=("Consolas", 12, "bold")
            ).pack(side=tk.LEFT)

            self._btn(top, "New Task", self._add_task_dialog).pack(side=tk.RIGHT, padx=2)
            self._btn(top, "Delete", self._delete_task).pack(side=tk.RIGHT, padx=2)
            self._btn(top, "Complete", self._complete_task).pack(side=tk.RIGHT, padx=2)
            self._btn(top, "Cancel", self._cancel_task).pack(side=tk.RIGHT, padx=2)

            # Filter
            filter_frame = tk.Frame(tab, bg="#1e1e2e")
            filter_frame.pack(fill=tk.X, padx=10, pady=2)
            tk.Label(filter_frame, text="Filter:", bg="#1e1e2e", fg="#cdd6f4").pack(side=tk.LEFT)
            self._task_filter_var = tk.StringVar(value="all")
            for val, lbl in [("all", "All"), ("pending", "Pending"),
                              ("in_progress", "In Progress"), ("completed", "Completed")]:
                tk.Radiobutton(
                    filter_frame, text=lbl, variable=self._task_filter_var,
                    value=val, bg="#1e1e2e", fg="#cdd6f4",
                    selectcolor="#313244", activebackground="#1e1e2e",
                    command=self._refresh_task_list
                ).pack(side=tk.LEFT, padx=5)

            task_cols = ("title", "priority", "status", "server", "created")
            self._task_tree = ttk.Treeview(
                tab, columns=task_cols, show="headings", height=20
            )
            for c, w in zip(task_cols, (250, 80, 100, 120, 150)):
                self._task_tree.heading(c, text=c.capitalize())
                self._task_tree.column(c, width=w, anchor=tk.W)
            self._task_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            # Detail
            self._task_detail = scrolledtext.ScrolledText(
                tab, bg="#313244", fg="#cdd6f4", font=("Consolas", 9),
                state=tk.DISABLED, height=5
            )
            self._task_detail.pack(fill=tk.X, padx=10, pady=(0, 5))
            self._task_tree.bind("<<TreeviewSelect>>", self._on_task_select)

        # ── helpers ────────────────────────────────────────────────────

        def _btn(self, parent, text: str, cmd) -> tk.Button:
            return tk.Button(
                parent, text=text, command=cmd,
                bg="#313244", fg="#cdd6f4",
                activebackground="#45475a", activeforeground="#cdd6f4",
                relief=tk.FLAT, padx=8, pady=4,
                font=("Consolas", 9),
                cursor="hand2",
            )

        def _set_text(self, widget: scrolledtext.ScrolledText, text: str) -> None:
            widget.configure(state=tk.NORMAL)
            widget.delete("1.0", tk.END)
            widget.insert(tk.END, text)
            widget.configure(state=tk.DISABLED)

        # ── server list ────────────────────────────────────────────────

        def _refresh_server_list(self) -> None:
            for item in self._srv_tree.get_children():
                self._srv_tree.delete(item)
            for cfg in self.ctrl.list_servers():
                status = self.ctrl.get_server_status(cfg.server_id)
                self._srv_tree.insert(
                    "", tk.END,
                    iid=cfg.server_id,
                    values=(cfg.name, cfg.host, cfg.port, status.value),
                )

        def _on_server_select(self, event=None) -> None:
            sel = self._srv_tree.selection()
            if not sel:
                return
            self._selected_server_id = sel[0]
            cfg = self.ctrl.server_manager.get_server(self._selected_server_id)
            if cfg:
                info = (
                    f"ID:          {cfg.server_id}\n"
                    f"Name:        {cfg.name}\n"
                    f"Host:        {cfg.host}\n"
                    f"Port:        {cfg.port}\n"
                    f"Description: {cfg.description}\n"
                    f"Status:      {self.ctrl.get_server_status(cfg.server_id).value}\n"
                )
                self._set_text(self._detail_text, info)
            self._refresh_processes()

        def _add_server_dialog(self) -> None:
            dlg = tk.Toplevel(self.root)
            dlg.title("Add Server")
            dlg.configure(bg="#1e1e2e")
            dlg.resizable(False, False)

            fields: Dict[str, tk.Entry] = {}
            for label, default in [
                ("Name", "My Server"),
                ("Host", "127.0.0.1"),
                ("Port", "9000"),
                ("Description", ""),
            ]:
                row = tk.Frame(dlg, bg="#1e1e2e")
                row.pack(fill=tk.X, padx=15, pady=4)
                tk.Label(row, text=label, bg="#1e1e2e", fg="#cdd6f4", width=12, anchor=tk.W).pack(side=tk.LEFT)
                e = tk.Entry(row, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", width=25)
                e.insert(0, default)
                e.pack(side=tk.LEFT)
                fields[label.lower()] = e

            def submit():
                try:
                    port = int(fields["port"].get())
                except ValueError:
                    messagebox.showerror("Error", "Port must be a number", parent=dlg)
                    return
                self.ctrl.add_server(
                    name=fields["name"].get(),
                    host=fields["host"].get(),
                    port=port,
                    description=fields["description"].get(),
                )
                self._refresh_server_list()
                dlg.destroy()

            self._btn(dlg, "Add Server", submit).pack(pady=10)

        def _remove_server(self) -> None:
            if not self._selected_server_id:
                return
            if messagebox.askyesno("Confirm", "Remove selected server?"):
                self.ctrl.remove_server(self._selected_server_id)
                self._selected_server_id = None
                self._refresh_server_list()

        def _connect_server(self) -> None:
            if not self._selected_server_id:
                return
            self.ctrl.connect_server(self._selected_server_id)
            self._status_var.set(f"Connecting to {self._selected_server_id}...")
            self._refresh_server_list()

        def _disconnect_server(self) -> None:
            if not self._selected_server_id:
                return
            self.ctrl.server_manager.disconnect(self._selected_server_id)
            self._refresh_server_list()

        # ── processes ──────────────────────────────────────────────────

        def _refresh_processes(self) -> None:
            for item in self._proc_tree.get_children():
                self._proc_tree.delete(item)
            if not self._selected_server_id:
                return
            procs = self.ctrl.get_processes(self._selected_server_id)
            for p in sorted(procs, key=lambda x: x.cpu_percent, reverse=True):
                self._proc_tree.insert(
                    "", tk.END,
                    iid=str(p.pid),
                    values=(
                        p.pid, p.name,
                        f"{p.cpu_percent:.1f}%",
                        f"{p.memory_mb:.1f} MB",
                        p.status, p.username,
                    ),
                )

        def _kill_selected_process(self) -> None:
            if not self._selected_server_id:
                messagebox.showwarning("Warning", "No server selected")
                return
            sel = self._proc_tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "No process selected")
                return
            pid = int(sel[0])
            if messagebox.askyesno("Confirm", f"Kill process {pid}?"):
                ok, msg = self.ctrl.kill_process(self._selected_server_id, pid)
                messagebox.showinfo("Result", msg)
                self._refresh_processes()

        # ── screen ─────────────────────────────────────────────────────

        def _view_screen(self) -> None:
            if not self._selected_server_id:
                messagebox.showwarning("Warning", "No server selected")
                return
            if Image is None:
                messagebox.showerror("Error", "Pillow not installed")
                return
            b64 = self.ctrl.get_screen(self._selected_server_id)
            if not b64:
                messagebox.showinfo("Screen", "No screen data available")
                return
            img_data = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_data))

            if self._screen_window and tk.Toplevel.winfo_exists(self._screen_window):
                self._screen_window.destroy()

            win = tk.Toplevel(self.root)
            win.title(f"Screen - {self._selected_server_id}")
            win.configure(bg="#1e1e2e")
            self._screen_window = win

            try:
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(win, image=photo, bg="#1e1e2e")
                lbl.image = photo
                lbl.pack()
            except ImportError:
                tk.Label(win, text="ImageTk not available", bg="#1e1e2e", fg="#cdd6f4").pack()

        # ── monitor tab ────────────────────────────────────────────────

        def _refresh_all_metrics(self) -> None:
            for widget in self._metrics_frame.winfo_children():
                widget.destroy()
            self._metric_cards.clear()

            servers = self.ctrl.list_servers()
            for i, cfg in enumerate(servers):
                metrics = self.ctrl.get_metrics(cfg.server_id)
                status = self.ctrl.get_server_status(cfg.server_id)

                card = tk.Frame(
                    self._metrics_frame, bg="#313244",
                    relief=tk.RIDGE, bd=1
                )
                card.grid(row=i // 3, column=i % 3, padx=5, pady=5, sticky="nsew")

                color = self.STATUS_COLORS.get(status, "#cc0000")
                tk.Label(
                    card, text=f"● {cfg.name}", bg="#313244",
                    fg=color, font=("Consolas", 10, "bold")
                ).pack(anchor=tk.W, padx=8, pady=(5, 2))

                if metrics:
                    tk.Label(
                        card,
                        text=(
                            f"CPU:  {metrics.cpu_percent:.1f}%\n"
                            f"RAM:  {metrics.ram_percent:.1f}% "
                            f"({metrics.ram_used_mb:.0f}/{metrics.ram_total_mb:.0f} MB)\n"
                            f"Net↑: {metrics.net_bytes_sent // 1024} KB\n"
                            f"Net↓: {metrics.net_bytes_recv // 1024} KB\n"
                            f"Procs: {len(metrics.processes)}"
                        ),
                        bg="#313244", fg="#cdd6f4",
                        font=("Consolas", 9), justify=tk.LEFT
                    ).pack(anchor=tk.W, padx=8, pady=(0, 5))
                else:
                    tk.Label(
                        card, text="No data", bg="#313244", fg="#6c7086",
                        font=("Consolas", 9)
                    ).pack(padx=8, pady=5)

            # History
            lines = []
            for cfg in servers:
                hist = self.ctrl.get_history(cfg.server_id)
                if hist:
                    last = hist[-1]
                    ts = datetime.fromtimestamp(last.timestamp).strftime("%H:%M:%S")
                    lines.append(
                        f"[{ts}] {cfg.name}: CPU={last.cpu_percent:.1f}% "
                        f"RAM={last.ram_percent:.1f}%"
                    )
            self._set_text(self._history_text, "\n".join(lines) if lines else "No history")

        # ── tasks ──────────────────────────────────────────────────────

        def _refresh_task_list(self) -> None:
            for item in self._task_tree.get_children():
                self._task_tree.delete(item)

            fval = self._task_filter_var.get() if hasattr(self, "_task_filter_var") else "all"
            status_filter = None if fval == "all" else TaskStatus(fval)
            tasks = self.ctrl.list_tasks(status=status_filter)

            priority_colors = {
                TaskPriority.CRITICAL: "#f38ba8",
                TaskPriority.HIGH: "#fab387",
                TaskPriority.MEDIUM: "#f9e2af",
                TaskPriority.LOW: "#a6e3a1",
            }

            for task in tasks:
                srv_name = ""
                if task.server_id:
                    cfg = self.ctrl.server_manager.get_server(task.server_id)
                    srv_name = cfg.name if cfg else task.server_id
                created = datetime.fromtimestamp(task.created_at).strftime("%Y-%m-%d %H:%M")
                iid = self._task_tree.insert(
                    "", tk.END,
                    iid=task.task_id,
                    values=(task.title, task.priority.value, task.status.value, srv_name, created),
                )
                color = priority_colors.get(task.priority, "#cdd6f4")
                self._task_tree.tag_configure(task.priority.value, foreground=color)
                self._task_tree.item(iid, tags=(task.priority.value,))

        def _on_task_select(self, event=None) -> None:
            sel = self._task_tree.selection()
            if not sel:
                return
            task = self.ctrl.task_manager.get_task(sel[0])
            if task:
                info = (
                    f"ID:          {task.task_id}\n"
                    f"Title:       {task.title}\n"
                    f"Priority:    {task.priority.value}\n"
                    f"Status:      {task.status.value}\n"
                    f"Server:      {task.server_id or 'N/A'}\n"
                    f"Description: {task.description}\n"
                    f"Created:     {datetime.fromtimestamp(task.created_at).strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                if task.completed_at:
                    info += f"Completed:   {datetime.fromtimestamp(task.completed_at).strftime('%Y-%m-%d %H:%M:%S')}\n"
                self._set_text(self._task_detail, info)

        def _add_task_dialog(self) -> None:
            dlg = tk.Toplevel(self.root)
            dlg.title("New Task")
            dlg.configure(bg="#1e1e2e")
            dlg.resizable(False, False)

            fields: Dict[str, Any] = {}

            for label, default in [("Title", "New Task"), ("Description", "")]:
                row = tk.Frame(dlg, bg="#1e1e2e")
                row.pack(fill=tk.X, padx=15, pady=4)
                tk.Label(row, text=label, bg="#1e1e2e", fg="#cdd6f4", width=12, anchor=tk.W).pack(side=tk.LEFT)
                e = tk.Entry(row, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", width=30)
                e.insert(0, default)
                e.pack(side=tk.LEFT)
                fields[label.lower()] = e

            # Priority
            row = tk.Frame(dlg, bg="#1e1e2e")
            row.pack(fill=tk.X, padx=15, pady=4)
            tk.Label(row, text="Priority", bg="#1e1e2e", fg="#cdd6f4", width=12, anchor=tk.W).pack(side=tk.LEFT)
            pvar = tk.StringVar(value="medium")
            for p in ["critical", "high", "medium", "low"]:
                tk.Radiobutton(
                    row, text=p, variable=pvar, value=p,
                    bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244",
                    activebackground="#1e1e2e"
                ).pack(side=tk.LEFT, padx=3)
            fields["priority"] = pvar

            # Server
            row = tk.Frame(dlg, bg="#1e1e2e")
            row.pack(fill=tk.X, padx=15, pady=4)
            tk.Label(row, text="Server", bg="#1e1e2e", fg="#cdd6f4", width=12, anchor=tk.W).pack(side=tk.LEFT)
            servers = self.ctrl.list_servers()
            srv_options = ["None"] + [f"{s.name} ({s.server_id})" for s in servers]
            srv_var = tk.StringVar(value="None")
            srv_map = {"None": None}
            for s in servers:
                srv_map[f"{s.name} ({s.server_id})"] = s.server_id
            om = ttk.OptionMenu(row, srv_var, "None", *srv_options)
            om.pack(side=tk.LEFT)
            fields["server"] = (srv_var, srv_map)

            def submit():
                srv_val, srv_m = fields["server"]
                server_id = srv_m.get(srv_val.get())
                self.ctrl.create_task(
                    title=fields["title"].get(),
                    description=fields["description"].get(),
                    priority=TaskPriority(fields["priority"].get()),
                    server_id=server_id,
                )
                self._refresh_task_list()
                dlg.destroy()

            self._btn(dlg, "Create Task", submit).pack(pady=10)

        def _get_selected_task_id(self) -> Optional[str]:
            sel = self._task_tree.selection()
            return sel[0] if sel else None

        def _complete_task(self) -> None:
            tid = self._get_selected_task_id()
            if tid:
                self.ctrl.complete_task(tid)
                self._refresh_task_list()

        def _cancel_task(self) -> None:
            tid = self._get_selected_task_id()
            if tid:
                self.ctrl.cancel_task(tid)
                self._refresh_task_list()

        def _delete_task(self) -> None:
            tid = self._get_selected_task_id()
            if tid and messagebox.askyesno("Confirm", "Delete selected task?"):
                self.ctrl.delete_task(tid)
                self._refresh_task_list()

        # ── auto refresh ───────────────────────────────────────────────

        def _start_auto_refresh(self) -> None:
            self._auto_refresh()

        def _auto_refresh(self) -> None:
            try:
                self._refresh_server_list()
                self._refresh_all_metrics()
                if self._selected_server_id:
                    self._refresh_processes()
            except Exception:
                pass
            self.root.after(3000, self._auto_refresh)

        def run(self) -> None:
            self.root.mainloop()


# ─────────────────────────────────────────────
# CLI interface
# ─────────────────────────────────────────────

class NexusCLI:
    def __init__(self, ctrl: NexusCtrl):
        self.ctrl = ctrl
        self._running = False

    def run(self) -> None:
        self._running = True
        print("NexusCtrl CLI - type 'help' for commands")
        while self._running:
            try:
                line = input("nexus> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            self._dispatch(cmd, args)

    def _dispatch(self, cmd: str, args: List[str]) -> None:
        handlers = {
            "help": self._help,
            "servers": self._list_servers,
            "add-server": self._add_server,
            "remove-server": self._remove_server,
            "connect": self._connect,
            "disconnect": self._disconnect,
            "metrics": self._metrics,
            "processes": self._processes,
            "kill": self._kill,
            "tasks": self._list_tasks,
            "add-task": self._add_task,
            "complete-task": self._complete_task,
            "delete-task": self._delete_task,
            "quit": self._quit,
            "exit": self._quit,
        }
        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")

    def _help(self, args: List[str]) -> None:
        print("""
Commands:
  servers                          List all servers
  add-server <name> <host> [port]  Add a server
  remove-server <server_id>        Remove a server
  connect <server_id>              Connect to server
  disconnect <server_id>           Disconnect from server
  metrics <server_id>              Show server metrics
  processes <server_id>            List processes
  kill <server_id> <pid>           Kill a process
  tasks [status]                   List tasks
  add-task <title>                 Add a task
  complete-task <task_id>          Mark task complete
  delete-task <task_id>            Delete a task
  quit / exit                      Exit
""")

    def _list_servers(self, args: List[str]) -> None:
        servers = self.ctrl.list_servers()
        if not servers:
            print("No servers configured.")
            return
        print(f"{'ID':<30} {'Name':<20} {'Host':<20} {'Port':<6} {'Status'}")
        print("-" * 90)
        for s in servers:
            status = self.ctrl.get_server_status(s.server_id)
            print(f"{s.server_id:<30} {s.name:<20} {s.host:<20} {s.port:<6} {status.value}")

    def _add_server(self, args: List[str]) -> None:
        if len(args) < 2:
            print("Usage: add-server <name> <host> [port]")
            return
        name, host = args[0], args[1]
        port = int(args[2]) if len(args) > 2 else 9000
        cfg = self.ctrl.add_server(name, host, port)
        print(f"Added server: {cfg.server_id}")

    def _remove_server(self, args: List[str]) -> None:
        if not args:
            print("Usage: remove-server <server_id>")
            return
        ok = self.ctrl.remove_server(args[0])
        print("Removed." if ok else "Server not found.")

    def _connect(self, args: List[str]) -> None:
        if not args:
            print("Usage: connect <server_id>")
            return
        conn = self.ctrl.connect_server(args[0])
        if conn:
            print(f"Connecting to {args[0]}...")
        else:
            print("Server not found.")

    def _disconnect(self, args: List[str]) -> None:
        if not args:
            print("Usage: disconnect <server_id>")
            return
        self.ctrl.server_manager.disconnect(args[0])
        print("Disconnected.")

    def _metrics(self, args: List[str]) -> None:
        if not args:
            print("Usage: metrics <server_id>")
            return
        m = self.ctrl.get_metrics(args[0])
        if m is None:
            print("No metrics available (server may not be connected).")
            return
        ts = datetime.fromtimestamp(m.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        print(f"Timestamp:  {ts}")
        print(f"CPU:        {m.cpu_percent:.1f}%")
        print(f"RAM:        {m.ram_percent:.1f}% ({m.ram_used_mb:.0f}/{m.ram_total_mb:.0f} MB)")
        print(f"Net Sent:   {m.net_bytes_sent // 1024} KB")
        print(f"Net Recv:   {m.net_bytes_recv // 1024} KB")
        print(f"Processes:  {len(m.processes)}")

    def _processes(self, args: List[str]) -> None:
        if not args:
            print("Usage: processes <server_id>")
            return
        procs = self.ctrl.get_processes(args[0])
        if not procs:
            print("No processes or server not connected.")
            return
        print(f"{'PID':<8} {'Name':<30} {'CPU%':<8} {'MEM(MB)':<10} {'Status':<12} {'User'}")
        print("-" * 80)
        for p in sorted(procs, key=lambda x: x.cpu_percent, reverse=True)[:30]:
            print(f"{p.pid:<8} {p.name[:29]:<30} {p.cpu_percent:<8.1f} {p.memory_mb:<10.1f} {p.status:<12} {p.username}")

    def _kill(self, args: List[str]) -> None:
        if len(args) < 2:
            print("Usage: kill <server_id> <pid>")
            return
        ok, msg = self.ctrl.kill_process(args[0], int(args[1]))
        print(f"{'OK' if ok else 'FAIL'}: {msg}")

    def _list_tasks(self, args: List[str]) -> None:
        status_filter = None
        if args:
            try:
                status_filter = TaskStatus(args[0])
            except ValueError:
                print(f"Invalid status: {args[0]}")
                return
        tasks = self.ctrl.list_tasks(status=status_filter)
        if not tasks:
            print("No tasks.")
            return
        print(f"{'ID':<35} {'Title':<30} {'Priority':<10} {'Status':<15} {'Server'}")
        print("-" * 100)
        for t in tasks:
            srv = t.server_id or "N/A"
            print(f"{t.task_id:<35} {t.title[:29]:<30} {t.priority.value:<10} {t.status.value:<15} {srv}")

    def _add_task(self, args: List[str]) -> None:
        if not args:
            print("Usage: add-task <title>")
            return
        title = " ".join(args)
        task = self.ctrl.create_task(title)
        print(f"Created task: {task.task_id}")

    def _complete_task(self, args: List[str]) -> None:
        if not args:
            print("Usage: complete-task <task_id>")
            return
        t = self.ctrl.complete_task(args[0])
        print("Task completed." if t else "Task not found.")

    def _delete_task(self, args: List[str]) -> None:
        if not args:
            print("Usage: delete-task <task_id>")
            return
        ok = self.ctrl.delete_task(args[0])
        print("Deleted." if ok else "Task not found.")

    def _quit(self, args: List[str]) -> None:
        self._running = False
        print("Goodbye.")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="NexusCtrl - RDP Server Management")
    parser.add_argument(
        "mode",
        nargs="?",
        default="gui",
        choices=["gui", "cli", "agent"],
        help="Run mode: gui (default), cli, or agent",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Agent bind host")
    parser.add_argument("--port", type=int, default=9000, help="Agent port")
    args = parser.parse_args()

    if args.mode == "agent":
        agent = Agent(host=args.host, port=args.port)
        print(f"Starting NexusCtrl Agent on {args.host}:{args.port}")
        try:
            agent.start()
        except KeyboardInterrupt:
            agent.stop()
            print("Agent stopped.")

    elif args.mode == "cli":
        ctrl = NexusCtrl()
        ctrl.connect_all()
        cli = NexusCLI(ctrl)
        try:
            cli.run()
        finally:
            ctrl.disconnect_all()

    else:  # gui
        ctrl = NexusCtrl()
        ctrl.connect_all()
        if HAS_TK:
            gui = NexusGUI(ctrl)
            try:
                gui.run()
            finally:
                ctrl.disconnect_all()
        else:
            print("Tkinter not available. Falling back to CLI mode.")
            cli = NexusCLI(ctrl)
            try:
                cli.run()
            finally:
                ctrl.disconnect_all()


if __name__ == "__main__":
    main()