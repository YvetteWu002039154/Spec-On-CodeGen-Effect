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
class SystemMetrics:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    net_bytes_sent: int = 0
    net_bytes_recv: int = 0
    net_sent_speed: float = 0.0
    net_recv_speed: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "net_bytes_sent": self.net_bytes_sent,
            "net_bytes_recv": self.net_bytes_recv,
            "net_sent_speed": self.net_sent_speed,
            "net_recv_speed": self.net_recv_speed,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SystemMetrics":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


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
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    server_id: Optional[str]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

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
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        d = dict(d)
        d["priority"] = TaskPriority(d["priority"])
        d["status"] = TaskStatus(d["status"])
        return cls(**d)


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
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


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
    except (json.JSONDecodeError, struct.error, OSError):
        return None


def _recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
    buf = b""
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except OSError:
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


# ─────────────────────────────────────────────
# Agent (runs on target machine)
# ─────────────────────────────────────────────

class AgentMetricsCollector:
    def __init__(self):
        self._prev_net = None
        self._prev_time = None

    def collect(self) -> SystemMetrics:
        metrics = SystemMetrics()
        if psutil is None:
            return metrics

        metrics.cpu_percent = psutil.cpu_percent(interval=0.1)

        vm = psutil.virtual_memory()
        metrics.ram_percent = vm.percent
        metrics.ram_used_mb = vm.used / (1024 * 1024)
        metrics.ram_total_mb = vm.total / (1024 * 1024)

        net = psutil.net_io_counters()
        now = time.time()
        metrics.net_bytes_sent = net.bytes_sent
        metrics.net_bytes_recv = net.bytes_recv

        if self._prev_net is not None and self._prev_time is not None:
            dt = now - self._prev_time
            if dt > 0:
                metrics.net_sent_speed = (net.bytes_sent - self._prev_net.bytes_sent) / dt
                metrics.net_recv_speed = (net.bytes_recv - self._prev_net.bytes_recv) / dt

        self._prev_net = net
        self._prev_time = now
        metrics.timestamp = now
        return metrics

    def get_processes(self) -> List[ProcessInfo]:
        if psutil is None:
            return []
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username"]):
            try:
                info = proc.info
                procs.append(ProcessInfo(
                    pid=info["pid"],
                    name=info["name"] or "",
                    cpu_percent=info["cpu_percent"] or 0.0,
                    memory_mb=(info["memory_info"].rss / (1024 * 1024)) if info["memory_info"] else 0.0,
                    status=info["status"] or "",
                    username=info["username"] or "",
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return procs

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        if psutil is None:
            return False, "psutil not available"
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return True, f"Process {pid} terminated"
        except psutil.NoSuchProcess:
            return False, f"Process {pid} not found"
        except psutil.AccessDenied:
            return False, f"Access denied for process {pid}"
        except Exception as e:
            return False, str(e)

    def capture_screen(self) -> Optional[str]:
        if ImageGrab is None:
            return None
        try:
            img = ImageGrab.grab()
            img.thumbnail((1280, 720), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None


class Agent:
    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self.collector = AgentMetricsCollector()
        self._running = False
        self._server_sock: Optional[socket.socket] = None

    def start(self) -> None:
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        print(f"[Agent] Listening on {self.host}:{self.port}")
        while self._running:
            try:
                self._server_sock.settimeout(1.0)
                try:
                    conn, addr = self._server_sock.accept()
                except socket.timeout:
                    continue
                print(f"[Agent] Connection from {addr}")
                t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                t.start()
            except OSError:
                break

    def stop(self) -> None:
        self._running = False
        if self._server_sock:
            self._server_sock.close()

    def _handle_client(self, conn: socket.socket) -> None:
        try:
            while True:
                msg = recv_message(conn)
                if msg is None:
                    break
                response = self._process_command(msg)
                send_message(conn, response)
        except Exception as e:
            print(f"[Agent] Client error: {e}")
        finally:
            conn.close()

    def _process_command(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        cmd = msg.get("command", "")
        if cmd == "get_metrics":
            metrics = self.collector.collect()
            return {"status": "ok", "metrics": metrics.to_dict()}
        elif cmd == "get_processes":
            procs = self.collector.get_processes()
            return {"status": "ok", "processes": [p.to_dict() for p in procs]}
        elif cmd == "kill_process":
            pid = msg.get("pid")
            if pid is None:
                return {"status": "error", "message": "No PID provided"}
            ok, message = self.collector.kill_process(int(pid))
            return {"status": "ok" if ok else "error", "message": message}
        elif cmd == "capture_screen":
            screenshot = self.collector.capture_screen()
            if screenshot:
                return {"status": "ok", "screenshot": screenshot}
            return {"status": "error", "message": "Screen capture failed"}
        elif cmd == "ping":
            return {"status": "ok", "message": "pong"}
        else:
            return {"status": "error", "message": f"Unknown command: {cmd}"}


# ─────────────────────────────────────────────
# Server Connection (client side)
# ─────────────────────────────────────────────

class ServerConnection:
    HISTORY_SIZE = 60

    def __init__(self, config: ServerConfig):
        self.config = config
        self.status = ServerStatus.OFFLINE
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self.metrics_history: deque = deque(maxlen=self.HISTORY_SIZE)
        self.last_metrics: Optional[SystemMetrics] = None
        self.last_processes: List[ProcessInfo] = []
        self.last_screenshot: Optional[str] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._polling = False

    @property
    def server_id(self) -> str:
        return self.config.server_id

    def connect(self) -> bool:
        with self._lock:
            try:
                self.status = ServerStatus.CONNECTING
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((self.config.host, self.config.port))
                sock.settimeout(10.0)
                self._sock = sock
                self.status = ServerStatus.ONLINE
                return True
            except Exception as e:
                self.status = ServerStatus.OFFLINE
                self._sock = None
                return False

    def disconnect(self) -> None:
        self.stop_polling()
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.status = ServerStatus.OFFLINE

    def _send_command(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._sock is None:
                return None
            try:
                send_message(self._sock, command)
                return recv_message(self._sock)
            except Exception:
                self.status = ServerStatus.OFFLINE
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
                return None

    def ping(self) -> bool:
        resp = self._send_command({"command": "ping"})
        return resp is not None and resp.get("status") == "ok"

    def fetch_metrics(self) -> Optional[SystemMetrics]:
        resp = self._send_command({"command": "get_metrics"})
        if resp and resp.get("status") == "ok":
            m = SystemMetrics.from_dict(resp["metrics"])
            self.last_metrics = m
            self.metrics_history.append(m)
            return m
        return None

    def fetch_processes(self) -> List[ProcessInfo]:
        resp = self._send_command({"command": "get_processes"})
        if resp and resp.get("status") == "ok":
            self.last_processes = [ProcessInfo.from_dict(p) for p in resp.get("processes", [])]
            return self.last_processes
        return []

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        resp = self._send_command({"command": "kill_process", "pid": pid})
        if resp is None:
            return False, "No response from agent"
        return resp.get("status") == "ok", resp.get("message", "")

    def capture_screen(self) -> Optional[str]:
        resp = self._send_command({"command": "capture_screen"})
        if resp and resp.get("status") == "ok":
            self.last_screenshot = resp.get("screenshot")
            return self.last_screenshot
        return None

    def start_polling(self, interval: float = 3.0) -> None:
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, args=(interval,), daemon=True
        )
        self._poll_thread.start()

    def stop_polling(self) -> None:
        self._polling = False

    def _poll_loop(self, interval: float) -> None:
        while self._polling:
            if self.status == ServerStatus.ONLINE:
                self.fetch_metrics()
                self.fetch_processes()
            elif self.status == ServerStatus.OFFLINE:
                self.connect()
            time.sleep(interval)

    def get_metrics_history(self) -> List[SystemMetrics]:
        return list(self.metrics_history)


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
                for item in data:
                    task = Task.from_dict(item)
                    self._tasks[task.task_id] = task
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
        description: str,
        priority: TaskPriority,
        server_id: Optional[str] = None,
    ) -> Task:
        with self._lock:
            task_id = f"task_{int(time.time() * 1000)}_{len(self._tasks)}"
            task = Task(
                task_id=task_id,
                title=title,
                description=description,
                priority=priority,
                status=TaskStatus.PENDING,
                server_id=server_id,
            )
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

    def complete_task(self, task_id: str) -> Optional[Task]:
        return self.update_task(task_id, status=TaskStatus.COMPLETED)

    def cancel_task(self, task_id: str) -> Optional[Task]:
        return self.update_task(task_id, status=TaskStatus.CANCELLED)


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
                for item in data:
                    cfg = ServerConfig.from_dict(item)
                    self._configs[cfg.server_id] = cfg
            except Exception:
                pass

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w") as f:
                json.dump([c.to_dict() for c in self._configs.values()], f, indent=2)
        except Exception:
            pass

    def add_server(self, name: str, host: str, port: int, description: str = "") -> ServerConfig:
        with self._lock:
            server_id = f"srv_{int(time.time() * 1000)}_{len(self._configs)}"
            cfg = ServerConfig(
                server_id=server_id,
                name=name,
                host=host,
                port=port,
                description=description,
            )
            self._configs[server_id] = cfg
            self._save()
            return cfg

    def remove_server(self, server_id: str) -> bool:
        with self._lock:
            if server_id in self._connections:
                self._connections[server_id].disconnect()
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

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        return self._configs.get(server_id)

    def list_servers(self) -> List[ServerConfig]:
        return list(self._configs.values())

    def get_connection(self, server_id: str) -> Optional[ServerConnection]:
        cfg = self._configs.get(server_id)
        if cfg is None:
            return None
        if server_id not in self._connections:
            self._connections[server_id] = ServerConnection(cfg)
        return self._connections[server_id]

    def connect_server(self, server_id: str) -> bool:
        conn = self.get_connection(server_id)
        if conn is None:
            return False
        return conn.connect()

    def disconnect_server(self, server_id: str) -> None:
        conn = self._connections.get(server_id)
        if conn:
            conn.disconnect()

    def connect_all(self) -> Dict[str, bool]:
        results = {}
        for server_id in self._configs:
            results[server_id] = self.connect_server(server_id)
        return results

    def disconnect_all(self) -> None:
        for conn in self._connections.values():
            conn.disconnect()

    def start_polling_all(self, interval: float = 3.0) -> None:
        for server_id in self._configs:
            conn = self.get_connection(server_id)
            if conn and conn.status == ServerStatus.ONLINE:
                conn.start_polling(interval)

    def get_all_statuses(self) -> Dict[str, ServerStatus]:
        result = {}
        for server_id, cfg in self._configs.items():
            conn = self._connections.get(server_id)
            result[server_id] = conn.status if conn else ServerStatus.OFFLINE
        return result


# ─────────────────────────────────────────────
# NexusCtrl Core
# ─────────────────────────────────────────────

class NexusCtrl:
    def __init__(
        self,
        servers_path: str = "nexus_servers.json",
        tasks_path: str = "nexus_tasks.json",
    ):
        self.server_manager = ServerManager(servers_path)
        self.task_manager = TaskManager(tasks_path)

    def add_server(self, name: str, host: str, port: int, description: str = "") -> ServerConfig:
        return self.server_manager.add_server(name, host, port, description)

    def remove_server(self, server_id: str) -> bool:
        return self.server_manager.remove_server(server_id)

    def connect(self, server_id: str) -> bool:
        return self.server_manager.connect_server(server_id)

    def disconnect(self, server_id: str) -> None:
        self.server_manager.disconnect_server(server_id)

    def connect_all(self) -> Dict[str, bool]:
        return self.server_manager.connect_all()

    def disconnect_all(self) -> None:
        self.server_manager.disconnect_all()

    def get_metrics(self, server_id: str) -> Optional[SystemMetrics]:
        conn = self.server_manager.get_connection(server_id)
        if conn and conn.status == ServerStatus.ONLINE:
            return conn.fetch_metrics()
        return None

    def get_processes(self, server_id: str) -> List[ProcessInfo]:
        conn = self.server_manager.get_connection(server_id)
        if conn and conn.status == ServerStatus.ONLINE:
            return conn.fetch_processes()
        return []

    def kill_process(self, server_id: str, pid: int) -> Tuple[bool, str]:
        conn = self.server_manager.get_connection(server_id)
        if conn and conn.status == ServerStatus.ONLINE:
            return conn.kill_process(pid)
        return False, "Server not connected"

    def capture_screen(self, server_id: str) -> Optional[str]:
        conn = self.server_manager.get_connection(server_id)
        if conn and conn.status == ServerStatus.ONLINE:
            return conn.capture_screen()
        return None

    def get_metrics_history(self, server_id: str) -> List[SystemMetrics]:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.get_metrics_history()
        return []

    def create_task(
        self,
        title: str,
        description: str,
        priority: TaskPriority,
        server_id: Optional[str] = None,
    ) -> Task:
        return self.task_manager.create_task(title, description, priority, server_id)

    def list_tasks(
        self,
        server_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
    ) -> List[Task]:
        return self.task_manager.list_tasks(server_id, status, priority)

    def complete_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.complete_task(task_id)

    def cancel_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.cancel_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        return self.task_manager.delete_task(task_id)

    def get_dashboard_summary(self) -> Dict[str, Any]:
        servers = self.server_manager.list_servers()
        statuses = self.server_manager.get_all_statuses()
        online = sum(1 for s in statuses.values() if s == ServerStatus.ONLINE)
        tasks = self.task_manager.list_tasks()
        pending = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        critical = sum(1 for t in tasks if t.priority == TaskPriority.CRITICAL and t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED))
        return {
            "total_servers": len(servers),
            "online_servers": online,
            "offline_servers": len(servers) - online,
            "total_tasks": len(tasks),
            "pending_tasks": pending,
            "in_progress_tasks": in_progress,
            "completed_tasks": completed,
            "critical_tasks": critical,
        }


# ─────────────────────────────────────────────
# GUI (Tkinter)
# ─────────────────────────────────────────────

if HAS_TK:

    class ServerDetailWindow(tk.Toplevel):
        def __init__(self, parent, nexus: NexusCtrl, server_id: str):
            super().__init__(parent)
            self.nexus = nexus
            self.server_id = server_id
            cfg = nexus.server_manager.get_server(server_id)
            self.title(f"Server: {cfg.name if cfg else server_id}")
            self.geometry("900x650")
            self._build_ui()
            self._refresh()

        def _build_ui(self):
            nb = ttk.Notebook(self)
            nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Metrics tab
            self.metrics_frame = ttk.Frame(nb)
            nb.add(self.metrics_frame, text="Metrics")
            self._build_metrics_tab()

            # Processes tab
            self.proc_frame = ttk.Frame(nb)
            nb.add(self.proc_frame, text="Processes")
            self._build_processes_tab()

            # Screen tab
            self.screen_frame = ttk.Frame(nb)
            nb.add(self.screen_frame, text="Screen")
            self._build_screen_tab()

            # History tab
            self.hist_frame = ttk.Frame(nb)
            nb.add(self.hist_frame, text="History")
            self._build_history_tab()

            btn_frame = ttk.Frame(self)
            btn_frame.pack(fill=tk.X, padx=5, pady=3)
            ttk.Button(btn_frame, text="Refresh", command=self._refresh).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=3)

        def _build_metrics_tab(self):
            f = self.metrics_frame
            self.cpu_var = tk.StringVar(value="CPU: --")
            self.ram_var = tk.StringVar(value="RAM: --")
            self.net_var = tk.StringVar(value="Network: --")
            ttk.Label(f, textvariable=self.cpu_var, font=("Arial", 14)).pack(pady=10)
            ttk.Label(f, textvariable=self.ram_var, font=("Arial", 14)).pack(pady=10)
            ttk.Label(f, textvariable=self.net_var, font=("Arial", 14)).pack(pady=10)

        def _build_processes_tab(self):
            f = self.proc_frame
            cols = ("PID", "Name", "CPU%", "Memory MB", "Status", "User")
            self.proc_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
            for c in cols:
                self.proc_tree.heading(c, text=c)
                self.proc_tree.column(c, width=120)
            vsb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.proc_tree.yview)
            self.proc_tree.configure(yscrollcommand=vsb.set)
            self.proc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            btn_f = ttk.Frame(self.proc_frame)
            btn_f.pack(fill=tk.X)
            ttk.Button(btn_f, text="Kill Selected", command=self._kill_selected).pack(side=tk.LEFT, padx=3, pady=3)
            ttk.Button(btn_f, text="Refresh Processes", command=self._refresh_processes).pack(side=tk.LEFT, padx=3)

        def _build_screen_tab(self):
            f = self.screen_frame
            self.screen_label = ttk.Label(f, text="No screenshot yet")
            self.screen_label.pack(expand=True)
            ttk.Button(f, text="Capture Screen", command=self._capture_screen).pack(pady=5)

        def _build_history_tab(self):
            f = self.hist_frame
            self.hist_text = scrolledtext.ScrolledText(f, state=tk.DISABLED, height=25)
            self.hist_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        def _refresh(self):
            self._refresh_metrics()
            self._refresh_processes()
            self._refresh_history()

        def _refresh_metrics(self):
            m = self.nexus.get_metrics(self.server_id)
            if m:
                self.cpu_var.set(f"CPU: {m.cpu_percent:.1f}%")
                self.ram_var.set(f"RAM: {m.ram_used_mb:.0f} MB / {m.ram_total_mb:.0f} MB ({m.ram_percent:.1f}%)")
                self.net_var.set(
                    f"Network ↑ {m.net_sent_speed / 1024:.1f} KB/s  ↓ {m.net_recv_speed / 1024:.1f} KB/s"
                )
            else:
                self.cpu_var.set("CPU: N/A")
                self.ram_var.set("RAM: N/A")
                self.net_var.set("Network: N/A")

        def _refresh_processes(self):
            for row in self.proc_tree.get_children():
                self.proc_tree.delete(row)
            procs = self.nexus.get_processes(self.server_id)
            for p in sorted(procs, key=lambda x: x.cpu_percent, reverse=True):
                self.proc_tree.insert(
                    "", tk.END,
                    values=(p.pid, p.name, f"{p.cpu_percent:.1f}", f"{p.memory_mb:.1f}", p.status, p.username),
                )

        def _kill_selected(self):
            sel = self.proc_tree.selection()
            if not sel:
                messagebox.showwarning("No selection", "Select a process first.")
                return
            item = self.proc_tree.item(sel[0])
            pid = int(item["values"][0])
            name = item["values"][1]
            if messagebox.askyesno("Confirm", f"Kill process {name} (PID {pid})?"):
                ok, msg = self.nexus.kill_process(self.server_id, pid)
                messagebox.showinfo("Result", msg)
                if ok:
                    self._refresh_processes()

        def _capture_screen(self):
            screenshot_b64 = self.nexus.capture_screen(self.server_id)
            if screenshot_b64 is None:
                messagebox.showerror("Error", "Failed to capture screen.")
                return
            try:
                img_data = base64.b64decode(screenshot_b64)
                img = Image.open(io.BytesIO(img_data))
                img.thumbnail((860, 540))
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(img)
                self.screen_label.configure(image=photo, text="")
                self.screen_label.image = photo
            except Exception as e:
                messagebox.showerror("Error", f"Could not display screenshot: {e}")

        def _refresh_history(self):
            history = self.nexus.get_metrics_history(self.server_id)
            self.hist_text.configure(state=tk.NORMAL)
            self.hist_text.delete("1.0", tk.END)
            for m in reversed(history):
                ts = datetime.fromtimestamp(m.timestamp).strftime("%H:%M:%S")
                line = (
                    f"[{ts}] CPU: {m.cpu_percent:.1f}%  "
                    f"RAM: {m.ram_percent:.1f}%  "
                    f"↑{m.net_sent_speed/1024:.1f}KB/s ↓{m.net_recv_speed/1024:.1f}KB/s\n"
                )
                self.hist_text.insert(tk.END, line)
            self.hist_text.configure(state=tk.DISABLED)


    class TaskDialog(tk.Toplevel):
        def __init__(self, parent, nexus: NexusCtrl, task: Optional[Task] = None, server_id: Optional[str] = None):
            super().__init__(parent)
            self.nexus = nexus
            self.task = task
            self.default_server_id = server_id
            self.result: Optional[Task] = None
            self.title("Edit Task" if task else "New Task")
            self.geometry("450x380")
            self.resizable(False, False)
            self._build()
            if task:
                self._populate(task)
            self.grab_set()

        def _build(self):
            f = ttk.Frame(self, padding=10)
            f.pack(fill=tk.BOTH, expand=True)

            ttk.Label(f, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=4)
            self.title_var = tk.StringVar()
            ttk.Entry(f, textvariable=self.title_var, width=40).grid(row=0, column=1, pady=4)

            ttk.Label(f, text="Description:").grid(row=1, column=0, sticky=tk.NW, pady=4)
            self.desc_text = tk.Text(f, width=30, height=5)
            self.desc_text.grid(row=1, column=1, pady=4)

            ttk.Label(f, text="Priority:").grid(row=2, column=0, sticky=tk.W, pady=4)
            self.priority_var = tk.StringVar(value=TaskPriority.MEDIUM.value)
            ttk.Combobox(
                f, textvariable=self.priority_var,
                values=[p.value for p in TaskPriority], state="readonly", width=15
            ).grid(row=2, column=1, sticky=tk.W, pady=4)

            ttk.Label(f, text="Status:").grid(row=3, column=0, sticky=tk.W, pady=4)
            self.status_var = tk.StringVar(value=TaskStatus.PENDING.value)
            ttk.Combobox(
                f, textvariable=self.status_var,
                values=[s.value for s in TaskStatus], state="readonly", width=15
            ).grid(row=3, column=1, sticky=tk.W, pady=4)

            ttk.Label(f, text="Server:").grid(row=4, column=0, sticky=tk.W, pady=4)
            servers = self.nexus.server_manager.list_servers()
            server_options = ["(none)"] + [f"{s.name} ({s.server_id})" for s in servers]
            self._server_map = {f"{s.name} ({s.server_id})": s.server_id for s in servers}
            self.server_var = tk.StringVar(value="(none)")
            ttk.Combobox(
                f, textvariable=self.server_var,
                values=server_options, state="readonly", width=30
            ).grid(row=4, column=1, sticky=tk.W, pady=4)

            btn_f = ttk.Frame(f)
            btn_f.grid(row=5, column=0, columnspan=2, pady=10)
            ttk.Button(btn_f, text="Save", command=self._save).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_f, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

        def _populate(self, task: Task):
            self.title_var.set(task.title)
            self.desc_text.insert("1.0", task.description)
            self.priority_var.set(task.priority.value)
            self.status_var.set(task.status.value)
            if task.server_id:
                for label, sid in self._server_map.items():
                    if sid == task.server_id:
                        self.server_var.set(label)
                        break

        def _save(self):
            title = self.title_var.get().strip()
            if not title:
                messagebox.showwarning("Validation", "Title is required.")
                return
            description = self.desc_text.get("1.0", tk.END).strip()
            priority = TaskPriority(self.priority_var.get())
            status = TaskStatus(self.status_var.get())
            server_label = self.server_var.get()
            server_id = self._server_map.get(server_label)

            if self.task:
                self.result = self.nexus.task_manager.update_task(
                    self.task.task_id,
                    title=title,
                    description=description,
                    priority=priority,
                    status=status,
                    server_id=server_id,
                )
            else:
                self.result = self.nexus.create_task(title, description, priority, server_id)
            self.destroy()


    class AddServerDialog(tk.Toplevel):
        def __init__(self, parent, nexus: NexusCtrl, server: Optional[ServerConfig] = None):
            super().__init__(parent)
            self.nexus = nexus
            self.server = server
            self.result: Optional[ServerConfig] = None
            self.title("Edit Server" if server else "Add Server")
            self.geometry("400x280")
            self.resizable(False, False)
            self._build()
            if server:
                self._populate(server)
            self.grab_set()

        def _build(self):
            f = ttk.Frame(self, padding=10)
            f.pack(fill=tk.BOTH, expand=True)

            fields = [("Name:", "name"), ("Host:", "host"), ("Port:", "port"), ("Description:", "desc")]
            self.vars = {}
            for i, (label, key) in enumerate(fields):
                ttk.Label(f, text=label).grid(row=i, column=0, sticky=tk.W, pady=5)
                var = tk.StringVar()
                ttk.Entry(f, textvariable=var, width=35).grid(row=i, column=1, pady=5)
                self.vars[key] = var

            self.vars["port"].set("9000")

            btn_f = ttk.Frame(f)
            btn_f.grid(row=len(fields), column=0, columnspan=2, pady=10)
            ttk.Button(btn_f, text="Save", command=self._save).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_f, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

        def _populate(self, s: ServerConfig):
            self.vars["name"].set(s.name)
            self.vars["host"].set(s.host)
            self.vars["port"].set(str(s.port))
            self.vars["desc"].set(s.description)

        def _save(self):
            name = self.vars["name"].get().strip()
            host = self.vars["host"].get().strip()
            port_str = self.vars["port"].get().strip()
            desc = self.vars["desc"].get().strip()

            if not name or not host:
                messagebox.showwarning("Validation", "Name and Host are required.")
                return
            try:
                port = int(port_str)
            except ValueError:
                messagebox.showwarning("Validation", "Port must be a number.")
                return

            if self.server:
                self.result = self.nexus.server_manager.update_server(
                    self.server.server_id, name=name, host=host, port=port, description=desc
                )
            else:
                self.result = self.nexus.add_server(name, host, port, desc)
            self.destroy()


    class NexusCtrlGUI:
        def __init__(self, nexus: NexusCtrl):
            self.nexus = nexus
            self.root = tk.Tk()
            self.root.title("NexusCtrl - RDP Server Management")
            self.root.geometry("1100x700")
            self._build_ui()
            self._refresh_loop()

        def _build_ui(self):
            # Menu
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            server_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Servers", menu=server_menu)
            server_menu.add_command(label="Add Server", command=self._add_server)
            server_menu.add_command(label="Connect All", command=self._connect_all)
            server_menu.add_command(label="Disconnect All", command=self._disconnect_all)

            task_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Tasks", menu=task_menu)
            task_menu.add_command(label="New Task", command=self._new_task)

            # Main layout
            paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
            paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Left: servers
            left_frame = ttk.LabelFrame(paned, text="Servers", width=350)
            paned.add(left_frame, weight=1)
            self._build_server_panel(left_frame)

            # Right: tasks + summary
            right_frame = ttk.Frame(paned)
            paned.add(right_frame, weight=2)
            self._build_right_panel(right_frame)

            # Status bar
            self.status_var = tk.StringVar(value="Ready")
            ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(
                fill=tk.X, side=tk.BOTTOM, padx=5, pady=2
            )

        def _build_server_panel(self, parent):
            btn_frame = ttk.Frame(parent)
            btn_frame.pack(fill=tk.X, padx=3, pady=3)
            ttk.Button(btn_frame, text="Add", command=self._add_server).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Edit", command=self._edit_server).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Remove", command=self._remove_server).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Connect", command=self._connect_selected).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Details", command=self._open_details).pack(side=tk.LEFT, padx=2)

            cols = ("Name", "Host", "Port", "Status")
            self.server_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
            for c in cols:
                self.server_tree.heading(c, text=c)
            self.server_tree.column("Name", width=100)
            self.server_tree.column("Host", width=120)
            self.server_tree.column("Port", width=50)
            self.server_tree.column("Status", width=70)
            vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.server_tree.yview)
            self.server_tree.configure(yscrollcommand=vsb.set)
            self.server_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=3)
            vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=3)
            self.server_tree.bind("<Double-1>", lambda e: self._open_details())

        def _build_right_panel(self, parent):
            # Summary
            summary_frame = ttk.LabelFrame(parent, text="Dashboard Summary")
            summary_frame.pack(fill=tk.X, padx=5, pady=5)
            self.summary_var = tk.StringVar(value="Loading...")
            ttk.Label(summary_frame, textvariable=self.summary_var, font=("Arial", 10)).pack(padx=5, pady=5)

            # Tasks
            task_frame = ttk.LabelFrame(parent, text="Tasks")
            task_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            btn_frame = ttk.Frame(task_frame)
            btn_frame.pack(fill=tk.X, padx=3, pady=3)
            ttk.Button(btn_frame, text="New Task", command=self._new_task).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Edit", command=self._edit_task).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Complete", command=self._complete_task).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Cancel", command=self._cancel_task).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Delete", command=self._delete_task).pack(side=tk.LEFT, padx=2)

            # Filter
            filter_frame = ttk.Frame(task_frame)
            filter_frame.pack(fill=tk.X, padx=3)
            ttk.Label(filter_frame, text="Filter Status:").pack(side=tk.LEFT)
            self.task_filter_var = tk.StringVar(value="all")
            ttk.Combobox(
                filter_frame, textvariable=self.task_filter_var,
                values=["all"] + [s.value for s in TaskStatus],
                state="readonly", width=12
            ).pack(side=tk.LEFT, padx=3)
            ttk.Button(filter_frame, text="Apply", command=self._refresh_tasks).pack(side=tk.LEFT, padx=2)

            cols = ("Title", "Priority", "Status", "Server", "Created")
            self.task_tree = ttk.Treeview(task_frame, columns=cols, show="headings", height=15)
            for c in cols:
                self.task_tree.heading(c, text=c)
            self.task_tree.column("Title", width=200)
            self.task_tree.column("Priority", width=80)
            self.task_tree.column("Status", width=90)
            self.task_tree.column("Server", width=100)
            self.task_tree.column("Created", width=130)
            vsb = ttk.Scrollbar(task_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
            self.task_tree.configure(yscrollcommand=vsb.set)
            self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=3)
            vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=3)
            self.task_tree.bind("<Double-1>", lambda e: self._edit_task())

        def _refresh_servers(self):
            for row in self.server_tree.get_children():
                self.server_tree.delete(row)
            servers = self.nexus.server_manager.list_servers()
            statuses = self.nexus.server_manager.get_all_statuses()
            for s in servers:
                status = statuses.get(s.server_id, ServerStatus.OFFLINE)
                tag = "online" if status == ServerStatus.ONLINE else "offline"
                self.server_tree.insert(
                    "", tk.END,
                    iid=s.server_id,
                    values=(s.name, s.host, s.port, status.value),
                    tags=(tag,),
                )
            self.server_tree.tag_configure("online", foreground="green")
            self.server_tree.tag_configure("offline", foreground="red")

        def _refresh_tasks(self):
            for row in self.task_tree.get_children():
                self.task_tree.delete(row)
            filter_val = self.task_filter_var.get()
            status_filter = None if filter_val == "all" else TaskStatus(filter_val)
            tasks = self.nexus.list_tasks(status=status_filter)
            priority_colors = {
                TaskPriority.CRITICAL: "red",
                TaskPriority.HIGH: "orange",
                TaskPriority.MEDIUM: "black",
                TaskPriority.LOW: "gray",
            }
            for t in tasks:
                server_name = ""
                if t.server_id:
                    cfg = self.nexus.server_manager.get_server(t.server_id)
                    server_name = cfg.name if cfg else t.server_id
                created = datetime.fromtimestamp(t.created_at).strftime("%Y-%m-%d %H:%M")
                self.task_tree.insert(
                    "", tk.END,
                    iid=t.task_id,
                    values=(t.title, t.priority.value, t.status.value, server_name, created),
                    tags=(t.priority.value,),
                )
            for p, color in priority_colors.items():
                self.task_tree.tag_configure(p.value, foreground=color)

        def _refresh_summary(self):
            s = self.nexus.get_dashboard_summary()
            text = (
                f"Servers: {s['online_servers']}/{s['total_servers']} online  |  "
                f"Tasks: {s['pending_tasks']} pending, {s['in_progress_tasks']} in progress, "
                f"{s['completed_tasks']} completed  |  Critical: {s['critical_tasks']}"
            )
            self.summary_var.set(text)

        def _refresh_loop(self):
            self._refresh_servers()
            self._refresh_tasks()
            self._refresh_summary()
            self.root.after(5000, self._refresh_loop)

        def _get_selected_server_id(self) -> Optional[str]:
            sel = self.server_tree.selection()
            return sel[0] if sel else None

        def _get_selected_task_id(self) -> Optional[str]:
            sel = self.task_tree.selection()
            return sel[0] if sel else None

        def _add_server(self):
            dlg = AddServerDialog(self.root, self.nexus)
            self.root.wait_window(dlg)
            if dlg.result:
                self.status_var.set(f"Server '{dlg.result.name}' added.")
                self._refresh_servers()

        def _edit_server(self):
            sid = self._get_selected_server_id()
            if not sid:
                messagebox.showwarning("No selection", "Select a server first.")
                return
            cfg = self.nexus.server_manager.get_server(sid)
            dlg = AddServerDialog(self.root, self.nexus, server=cfg)
            self.root.wait_window(dlg)
            if dlg.result:
                self.status_var.set(f"Server '{dlg.result.name}' updated.")
                self._refresh_servers()

        def _remove_server(self):
            sid = self._get_selected_server_id()
            if not sid:
                messagebox.showwarning("No selection", "Select a server first.")
                return
            cfg = self.nexus.server_manager.get_server(sid)
            if messagebox.askyesno("Confirm", f"Remove server '{cfg.name}'?"):
                self.nexus.remove_server(sid)
                self.status_var.set(f"Server '{cfg.name}' removed.")
                self._refresh_servers()

        def _connect_selected(self):
            sid = self._get_selected_server_id()
            if not sid:
                messagebox.showwarning("No selection", "Select a server first.")
                return
            self.status_var.set("Connecting...")
            self.root.update()
            ok = self.nexus.connect(sid)
            cfg = self.nexus.server_manager.get_server(sid)
            if ok:
                conn = self.nexus.server_manager.get_connection(sid)
                if conn:
                    conn.start_polling()
                self.status_var.set(f"Connected to '{cfg.name}'.")
            else:
                self.status_var.set(f"Failed to connect to '{cfg.name}'.")
            self._refresh_servers()

        def _connect_all(self):
            self.status_var.set("Connecting to all servers...")
            self.root.update()
            results = self.nexus.connect_all()
            ok_count = sum(1 for v in results.values() if v)
            for sid, ok in results.items():
                if ok:
                    conn = self.nexus.server_manager.get_connection(sid)
                    if conn:
                        conn.start_polling()
            self.status_var.set(f"Connected to {ok_count}/{len(results)} servers.")
            self._refresh_servers()

        def _disconnect_all(self):
            self.nexus.disconnect_all()
            self.status_var.set("Disconnected from all servers.")
            self._refresh_servers()

        def _open_details(self):
            sid = self._get_selected_server_id()
            if not sid:
                messagebox.showwarning("No selection", "Select a server first.")
                return
            conn = self.nexus.server_manager.get_connection(sid)
            if conn is None or conn.status != ServerStatus.ONLINE:
                messagebox.showwarning("Not connected", "Connect to the server first.")
                return
            ServerDetailWindow(self.root, self.nexus, sid)

        def _new_task(self):
            sid = self._get_selected_server_id()
            dlg = TaskDialog(self.root, self.nexus, server_id=sid)
            self.root.wait_window(dlg)
            if dlg.result:
                self.status_var.set(f"Task '{dlg.result.title}' created.")
                self._refresh_tasks()
                self._refresh_summary()

        def _edit_task(self):
            tid = self._get_selected_task_id()
            if not tid:
                messagebox.showwarning("No selection", "Select a task first.")
                return
            task = self.nexus.task_manager.get_task(tid)
            dlg = TaskDialog(self.root, self.nexus, task=task)
            self.root.wait_window(dlg)
            if dlg.result:
                self.status_var.set(f"Task '{dlg.result.title}' updated.")
                self._refresh_tasks()
                self._refresh_summary()

        def _complete_task(self):
            tid = self._get_selected_task_id()
            if not tid:
                messagebox.showwarning("No selection", "Select a task first.")
                return
            task = self.nexus.task_manager.complete_task(tid)
            if task:
                self.status_var.set(f"Task '{task.title}' marked as completed.")
                self._refresh_tasks()
                self._refresh_summary()

        def _cancel_task(self):
            tid = self._get_selected_task_id()
            if not tid:
                messagebox.showwarning("No selection", "Select a task first.")
                return
            task = self.nexus.task_manager.cancel_task(tid)
            if task:
                self.status_var.set(f"Task '{task.title}' cancelled.")
                self._refresh_tasks()
                self._refresh_summary()

        def _delete_task(self):
            tid = self._get_selected_task_id()
            if not tid:
                messagebox.showwarning("No selection", "Select a task first.")
                return
            task = self.nexus.task_manager.get_task(tid)
            if task and messagebox.askyesno("Confirm", f"Delete task '{task.title}'?"):
                self.nexus.delete_task(tid)
                self.status_var.set(f"Task '{task.title}' deleted.")
                self._refresh_tasks()
                self._refresh_summary()

        def run(self):
            self.root.mainloop()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

class NexusCLI:
    def __init__(self, nexus: NexusCtrl):
        self.nexus = nexus
        self.commands = {
            "help": self._cmd_help,
            "servers": self._cmd_servers,
            "add-server": self._cmd_add_server,
            "remove-server": self._cmd_remove_server,
            "connect": self._cmd_connect,
            "disconnect": self._cmd_disconnect,
            "metrics": self._cmd_metrics,
            "processes": self._cmd_processes,
            "kill": self._cmd_kill,
            "screenshot": self._cmd_screenshot,
            "tasks": self._cmd_tasks,
            "add-task": self._cmd_add_task,
            "complete-task": self._cmd_complete_task,
            "cancel-task": self._cmd_cancel_task,
            "delete-task": self._cmd_delete_task,
            "summary": self._cmd_summary,
            "exit": self._cmd_exit,
        }

    def run(self):
        print("NexusCtrl CLI - Type 'help' for commands")
        while True:
            try:
                line = input("nexus> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            handler = self.commands.get(cmd)
            if handler:
                try:
                    handler(args)
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print(f"Unknown command: {cmd}. Type 'help' for commands.")

    def _cmd_help(self, args):
        print("Available commands:")
        for cmd in sorted(self.commands):
            print(f"  {cmd}")

    def _cmd_servers(self, args):
        servers = self.nexus.server_manager.list_servers()
        statuses = self.nexus.server_manager.get_all_statuses()
        if not servers:
            print("No servers configured.")
            return
        print(f"{'ID':<30} {'Name':<20} {'Host':<20} {'Port':<6} {'Status'}")
        print("-" * 90)
        for s in servers:
            status = statuses.get(s.server_id, ServerStatus.OFFLINE)
            print(f"{s.server_id:<30} {s.name:<20} {s.host:<20} {s.port:<6} {status.value}")

    def _cmd_add_server(self, args):
        name = input("Name: ").strip()
        host = input("Host: ").strip()
        port_str = input("Port [9000]: ").strip() or "9000"
        desc = input("Description: ").strip()
        try:
            port = int(port_str)
        except ValueError:
            print("Invalid port.")
            return
        cfg = self.nexus.add_server(name, host, port, desc)
        print(f"Server added: {cfg.server_id}")

    def _cmd_remove_server(self, args):
        if not args:
            print("Usage: remove-server <server_id>")
            return
        ok = self.nexus.remove_server(args[0])
        print("Removed." if ok else "Server not found.")

    def _cmd_connect(self, args):
        if not args:
            print("Usage: connect <server_id>")
            return
        ok = self.nexus.connect(args[0])
        if ok:
            conn = self.nexus.server_manager.get_connection(args[0])
            if conn:
                conn.start_polling()
        print("Connected." if ok else "Failed to connect.")

    def _cmd_disconnect(self, args):
        if not args:
            print("Usage: disconnect <server_id>")
            return
        self.nexus.disconnect(args[0])
        print("Disconnected.")

    def _cmd_metrics(self, args):
        if not args:
            print("Usage: metrics <server_id>")
            return
        m = self.nexus.get_metrics(args[0])
        if m is None:
            print("Could not fetch metrics (server offline?).")
            return
        print(f"CPU:     {m.cpu_percent:.1f}%")
        print(f"RAM:     {m.ram_used_mb:.0f} MB / {m.ram_total_mb:.0f} MB ({m.ram_percent:.1f}%)")
        print(f"Net ↑:   {m.net_sent_speed/1024:.1f} KB/s")
        print(f"Net ↓:   {m.net_recv_speed/1024:.1f} KB/s")

    def _cmd_processes(self, args):
        if not args:
            print("Usage: processes <server_id>")
            return
        procs = self.nexus.get_processes(args[0])
        if not procs:
            print("No processes or server offline.")
            return
        print(f"{'PID':<8} {'Name':<30} {'CPU%':<8} {'Mem MB':<10} {'Status'}")
        print("-" * 70)
        for p in sorted(procs, key=lambda x: x.cpu_percent, reverse=True)[:30]:
            print(f"{p.pid:<8} {p.name:<30} {p.cpu_percent:<8.1f} {p.memory_mb:<10.1f} {p.status}")

    def _cmd_kill(self, args):
        if len(args) < 2:
            print("Usage: kill <server_id> <pid>")
            return
        try:
            pid = int(args[1])
        except ValueError:
            print("Invalid PID.")
            return
        ok, msg = self.nexus.kill_process(args[0], pid)
        print(msg)

    def _cmd_screenshot(self, args):
        if not args:
            print("Usage: screenshot <server_id> [output_file]")
            return
        screenshot = self.nexus.capture_screen(args[0])
        if screenshot is None:
            print("Failed to capture screenshot.")
            return
        out_file = args[1] if len(args) > 1 else f"screenshot_{args[0]}_{int(time.time())}.jpg"
        with open(out_file, "wb") as f:
            f.write(base64.b64decode(screenshot))
        print(f"Screenshot saved to {out_file}")

    def _cmd_tasks(self, args):
        tasks = self.nexus.list_tasks()
        if not tasks:
            print("No tasks.")
            return
        print(f"{'ID':<35} {'Title':<30} {'Priority':<10} {'Status':<15} {'Server'}")
        print("-" * 100)
        for t in tasks:
            server_name = ""
            if t.server_id:
                cfg = self.nexus.server_manager.get_server(t.server_id)
                server_name = cfg.name if cfg else t.server_id
            print(f"{t.task_id:<35} {t.title:<30} {t.priority.value:<10} {t.status.value:<15} {server_name}")

    def _cmd_add_task(self, args):
        title = input("Title: ").strip()
        description = input("Description: ").strip()
        print("Priority options:", ", ".join(p.value for p in TaskPriority))
        priority_str = input("Priority [medium]: ").strip() or "medium"
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            print("Invalid priority.")
            return
        server_id_input = input("Server ID (leave blank for none): ").strip() or None
        task = self.nexus.create_task(title, description, priority, server_id_input)
        print(f"Task created: {task.task_id}")

    def _cmd_complete_task(self, args):
        if not args:
            print("Usage: complete-task <task_id>")
            return
        task = self.nexus.complete_task(args[0])
        print("Task completed." if task else "Task not found.")

    def _cmd_cancel_task(self, args):
        if not args:
            print("Usage: cancel-task <task_id>")
            return
        task = self.nexus.cancel_task(args[0])
        print("Task cancelled." if task else "Task not found.")

    def _cmd_delete_task(self, args):
        if not args:
            print("Usage: delete-task <task_id>")
            return
        ok = self.nexus.delete_task(args[0])
        print("Task deleted." if ok else "Task not found.")

    def _cmd_summary(self, args):
        s = self.nexus.get_dashboard_summary()
        print("=== Dashboard Summary ===")
        print(f"Servers:  {s['online_servers']}/{s['total_servers']} online")
        print(f"Tasks:    {s['pending_tasks']} pending | {s['in_progress_tasks']} in progress | {s['completed_tasks']} completed")
        print(f"Critical: {s['critical_tasks']} active critical tasks")

    def _cmd_exit(self, args):
        self.nexus.disconnect_all()
        print("Goodbye.")
        sys.exit(0)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def run_agent(host: str = "0.0.0.0", port: int = 9000):
    agent = Agent(host, port)
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
        print("[Agent] Stopped.")


def run_gui():
    if not HAS_TK:
        print("Tkinter not available. Use CLI mode.")
        return
    nexus = NexusCtrl()
    app = NexusCtrlGUI(nexus)
    app.run()


def run_cli():
    nexus = NexusCtrl()
    cli = NexusCLI(nexus)
    cli.run()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="NexusCtrl - RDP Server Management Tool")
    parser.add_argument(
        "mode",
        choices=["gui", "cli", "agent"],
        nargs="?",
        default="gui",
        help="Run mode: gui (default), cli, or agent",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Agent bind host")
    parser.add_argument("--port", type=int, default=9000, help="Agent port")
    args = parser.parse_args()

    if args.mode == "agent":
        run_agent(args.host, args.port)
    elif args.mode == "cli":
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()