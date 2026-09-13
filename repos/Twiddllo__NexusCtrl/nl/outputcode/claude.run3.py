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
            "memory_mb": round(self.memory_mb, 2),
            "status": self.status,
            "username": self.username,
        }


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
            "ram_used_mb": round(self.ram_used_mb, 2),
            "ram_total_mb": round(self.ram_total_mb, 2),
            "net_bytes_sent": self.net_bytes_sent,
            "net_bytes_recv": self.net_bytes_recv,
            "processes": [p.to_dict() for p in self.processes],
        }


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
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            task_id=data["task_id"],
            title=data["title"],
            description=data["description"],
            priority=TaskPriority(data["priority"]),
            status=TaskStatus(data["status"]),
            server_id=data.get("server_id"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            completed_at=data.get("completed_at"),
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
    def from_dict(cls, data: Dict[str, Any]) -> "ServerConfig":
        return cls(
            server_id=data["server_id"],
            name=data["name"],
            host=data["host"],
            port=int(data["port"]),
            description=data.get("description", ""),
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
    buf = b""
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except Exception:
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


# ─────────────────────────────────────────────
# Agent (runs on target machine)
# ─────────────────────────────────────────────

class AgentMetricsCollector:
    """Collects system metrics on the agent machine."""

    def __init__(self):
        self._prev_net = None

    def collect(self) -> SystemMetrics:
        if psutil is None:
            raise RuntimeError("psutil is required for the agent")

        cpu = psutil.cpu_percent(interval=0.5)
        vm = psutil.virtual_memory()
        net = psutil.net_io_counters()

        sent = net.bytes_sent
        recv = net.bytes_recv

        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username"]):
            try:
                info = proc.info
                mem_mb = info["memory_info"].rss / (1024 * 1024) if info["memory_info"] else 0.0
                processes.append(ProcessInfo(
                    pid=info["pid"],
                    name=info["name"] or "",
                    cpu_percent=info["cpu_percent"] or 0.0,
                    memory_mb=mem_mb,
                    status=info["status"] or "",
                    username=info["username"] or "",
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=cpu,
            ram_percent=vm.percent,
            ram_used_mb=vm.used / (1024 * 1024),
            ram_total_mb=vm.total / (1024 * 1024),
            net_bytes_sent=sent,
            net_bytes_recv=recv,
            processes=processes,
        )

    def capture_screen(self) -> Optional[str]:
        """Capture screen and return as base64-encoded JPEG."""
        if ImageGrab is None:
            return None
        try:
            img = ImageGrab.grab()
            img = img.resize((1280, 720), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

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


class Agent:
    """Background agent that runs on target machines."""

    DEFAULT_PORT = 9876

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._collector = AgentMetricsCollector()
        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)
        print(f"[Agent] Listening on {self.host}:{self.port}")
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_client(self, conn: socket.socket, addr: Tuple) -> None:
        print(f"[Agent] Connection from {addr}")
        conn.settimeout(30.0)
        try:
            while True:
                msg = recv_message(conn)
                if msg is None:
                    break
                response = self._dispatch(msg)
                send_message(conn, response)
        except Exception as e:
            print(f"[Agent] Client error: {e}")
        finally:
            conn.close()

    def _dispatch(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        cmd = msg.get("cmd", "")
        if cmd == "get_metrics":
            try:
                metrics = self._collector.collect()
                return {"status": "ok", "metrics": metrics.to_dict()}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif cmd == "get_screen":
            screenshot = self._collector.capture_screen()
            if screenshot:
                return {"status": "ok", "screenshot": screenshot}
            return {"status": "error", "message": "Screen capture failed"}
        elif cmd == "kill_process":
            pid = msg.get("pid")
            if pid is None:
                return {"status": "error", "message": "No PID provided"}
            success, message = self._collector.kill_process(int(pid))
            return {"status": "ok" if success else "error", "message": message}
        elif cmd == "ping":
            return {"status": "ok", "pong": True, "timestamp": time.time()}
        else:
            return {"status": "error", "message": f"Unknown command: {cmd}"}

    def run_forever(self) -> None:
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[Agent] Shutting down...")
            self.stop()


# ─────────────────────────────────────────────
# Server Connection (client side)
# ─────────────────────────────────────────────

class ServerConnection:
    """Manages connection to a single agent."""

    HISTORY_SIZE = 300  # ~5 minutes at 1s intervals

    def __init__(self, config: ServerConfig):
        self.config = config
        self.status = ServerStatus.OFFLINE
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._metrics_history: deque = deque(maxlen=self.HISTORY_SIZE)
        self._last_metrics: Optional[SystemMetrics] = None
        self._last_screenshot: Optional[str] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False

    @property
    def server_id(self) -> str:
        return self.config.server_id

    @property
    def name(self) -> str:
        return self.config.name

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
        self.stop_monitoring()
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.status = ServerStatus.OFFLINE

    def _send_command(self, cmd: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._sock is None:
                return None
            try:
                send_message(self._sock, cmd)
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
        resp = self._send_command({"cmd": "ping"})
        if resp and resp.get("status") == "ok":
            self.status = ServerStatus.ONLINE
            return True
        self.status = ServerStatus.OFFLINE
        return False

    def get_metrics(self) -> Optional[SystemMetrics]:
        resp = self._send_command({"cmd": "get_metrics"})
        if resp and resp.get("status") == "ok":
            data = resp["metrics"]
            processes = [
                ProcessInfo(
                    pid=p["pid"],
                    name=p["name"],
                    cpu_percent=p["cpu_percent"],
                    memory_mb=p["memory_mb"],
                    status=p["status"],
                    username=p.get("username", ""),
                )
                for p in data.get("processes", [])
            ]
            metrics = SystemMetrics(
                timestamp=data["timestamp"],
                cpu_percent=data["cpu_percent"],
                ram_percent=data["ram_percent"],
                ram_used_mb=data["ram_used_mb"],
                ram_total_mb=data["ram_total_mb"],
                net_bytes_sent=data["net_bytes_sent"],
                net_bytes_recv=data["net_bytes_recv"],
                processes=processes,
            )
            self._last_metrics = metrics
            self._metrics_history.append(metrics)
            return metrics
        return None

    def get_screenshot(self) -> Optional[str]:
        resp = self._send_command({"cmd": "get_screen"})
        if resp and resp.get("status") == "ok":
            self._last_screenshot = resp.get("screenshot")
            return self._last_screenshot
        return None

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        resp = self._send_command({"cmd": "kill_process", "pid": pid})
        if resp:
            return resp.get("status") == "ok", resp.get("message", "")
        return False, "No response from agent"

    def get_metrics_history(self) -> List[SystemMetrics]:
        return list(self._metrics_history)

    def get_last_metrics(self) -> Optional[SystemMetrics]:
        return self._last_metrics

    def get_last_screenshot(self) -> Optional[str]:
        return self._last_screenshot

    def start_monitoring(self, interval: float = 2.0) -> None:
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True
        )
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._monitoring = False

    def _monitor_loop(self, interval: float) -> None:
        while self._monitoring:
            if self.status == ServerStatus.ONLINE:
                self.get_metrics()
            elif self.status == ServerStatus.OFFLINE:
                self.connect()
            time.sleep(interval)


# ─────────────────────────────────────────────
# Task Manager
# ─────────────────────────────────────────────

class TaskManager:
    """Manages tasks with persistence."""

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

    def _generate_id(self) -> str:
        return f"task_{int(time.time() * 1000)}_{len(self._tasks)}"

    def create_task(
        self,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        server_id: Optional[str] = None,
    ) -> Task:
        with self._lock:
            now = time.time()
            task = Task(
                task_id=self._generate_id(),
                title=title,
                description=description,
                priority=priority,
                status=TaskStatus.PENDING,
                server_id=server_id,
                created_at=now,
                updated_at=now,
            )
            self._tasks[task.task_id] = task
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

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def get_tasks_by_server(self, server_id: str) -> List[Task]:
        return [t for t in self._tasks.values() if t.server_id == server_id]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == status]

    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        return [t for t in self._tasks.values() if t.priority == priority]


# ─────────────────────────────────────────────
# Server Manager
# ─────────────────────────────────────────────

class ServerManager:
    """Manages multiple server connections."""

    def __init__(self, config_path: str = "servers.json"):
        self.config_path = config_path
        self._servers: Dict[str, ServerConnection] = {}
        self._lock = threading.Lock()
        self._load_configs()

    def _load_configs(self) -> None:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                for item in data:
                    cfg = ServerConfig.from_dict(item)
                    conn = ServerConnection(cfg)
                    self._servers[cfg.server_id] = conn
            except Exception:
                pass

    def _save_configs(self) -> None:
        try:
            configs = [s.config.to_dict() for s in self._servers.values()]
            with open(self.config_path, "w") as f:
                json.dump(configs, f, indent=2)
        except Exception:
            pass

    def add_server(self, name: str, host: str, port: int, description: str = "") -> ServerConfig:
        with self._lock:
            server_id = f"srv_{int(time.time() * 1000)}"
            cfg = ServerConfig(
                server_id=server_id,
                name=name,
                host=host,
                port=port,
                description=description,
            )
            conn = ServerConnection(cfg)
            self._servers[server_id] = conn
            self._save_configs()
            return cfg

    def remove_server(self, server_id: str) -> bool:
        with self._lock:
            if server_id in self._servers:
                self._servers[server_id].disconnect()
                del self._servers[server_id]
                self._save_configs()
                return True
            return False

    def get_server(self, server_id: str) -> Optional[ServerConnection]:
        return self._servers.get(server_id)

    def get_all_servers(self) -> List[ServerConnection]:
        return list(self._servers.values())

    def connect_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server:
            return server.connect()
        return False

    def disconnect_server(self, server_id: str) -> None:
        server = self._servers.get(server_id)
        if server:
            server.disconnect()

    def connect_all(self) -> None:
        for server in self._servers.values():
            t = threading.Thread(target=server.connect, daemon=True)
            t.start()

    def start_monitoring_all(self, interval: float = 2.0) -> None:
        for server in self._servers.values():
            server.start_monitoring(interval)

    def stop_monitoring_all(self) -> None:
        for server in self._servers.values():
            server.stop_monitoring()


# ─────────────────────────────────────────────
# GUI Application
# ─────────────────────────────────────────────

if HAS_TK:

    class AddServerDialog(tk.Toplevel):
        def __init__(self, parent):
            super().__init__(parent)
            self.title("Add Server")
            self.resizable(False, False)
            self.result: Optional[Dict[str, Any]] = None
            self._build()
            self.grab_set()

        def _build(self):
            pad = {"padx": 8, "pady": 4}
            tk.Label(self, text="Name:").grid(row=0, column=0, sticky="e", **pad)
            self._name = tk.Entry(self, width=30)
            self._name.grid(row=0, column=1, **pad)

            tk.Label(self, text="Host:").grid(row=1, column=0, sticky="e", **pad)
            self._host = tk.Entry(self, width=30)
            self._host.grid(row=1, column=1, **pad)

            tk.Label(self, text="Port:").grid(row=2, column=0, sticky="e", **pad)
            self._port = tk.Entry(self, width=30)
            self._port.insert(0, str(Agent.DEFAULT_PORT))
            self._port.grid(row=2, column=1, **pad)

            tk.Label(self, text="Description:").grid(row=3, column=0, sticky="e", **pad)
            self._desc = tk.Entry(self, width=30)
            self._desc.grid(row=3, column=1, **pad)

            btn_frame = tk.Frame(self)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
            tk.Button(btn_frame, text="Add", command=self._ok, width=10).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=4)

        def _ok(self):
            name = self._name.get().strip()
            host = self._host.get().strip()
            try:
                port = int(self._port.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Port must be a number", parent=self)
                return
            if not name or not host:
                messagebox.showerror("Error", "Name and host are required", parent=self)
                return
            self.result = {
                "name": name,
                "host": host,
                "port": port,
                "description": self._desc.get().strip(),
            }
            self.destroy()

    class AddTaskDialog(tk.Toplevel):
        def __init__(self, parent, servers: List[ServerConnection]):
            super().__init__(parent)
            self.title("Add Task")
            self.resizable(False, False)
            self.result: Optional[Dict[str, Any]] = None
            self._servers = servers
            self._build()
            self.grab_set()

        def _build(self):
            pad = {"padx": 8, "pady": 4}
            tk.Label(self, text="Title:").grid(row=0, column=0, sticky="e", **pad)
            self._title = tk.Entry(self, width=35)
            self._title.grid(row=0, column=1, **pad)

            tk.Label(self, text="Description:").grid(row=1, column=0, sticky="ne", **pad)
            self._desc = tk.Text(self, width=35, height=4)
            self._desc.grid(row=1, column=1, **pad)

            tk.Label(self, text="Priority:").grid(row=2, column=0, sticky="e", **pad)
            self._priority = ttk.Combobox(
                self,
                values=[p.value for p in TaskPriority],
                state="readonly",
                width=32,
            )
            self._priority.set(TaskPriority.MEDIUM.value)
            self._priority.grid(row=2, column=1, **pad)

            tk.Label(self, text="Server:").grid(row=3, column=0, sticky="e", **pad)
            server_options = ["(none)"] + [f"{s.name} ({s.server_id})" for s in self._servers]
            self._server_var = tk.StringVar(value="(none)")
            self._server_combo = ttk.Combobox(
                self,
                textvariable=self._server_var,
                values=server_options,
                state="readonly",
                width=32,
            )
            self._server_combo.grid(row=3, column=1, **pad)

            btn_frame = tk.Frame(self)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
            tk.Button(btn_frame, text="Create", command=self._ok, width=10).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=4)

        def _ok(self):
            title = self._title.get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required", parent=self)
                return
            server_id = None
            sel = self._server_var.get()
            if sel != "(none)":
                for s in self._servers:
                    if f"{s.name} ({s.server_id})" == sel:
                        server_id = s.server_id
                        break
            self.result = {
                "title": title,
                "description": self._desc.get("1.0", tk.END).strip(),
                "priority": TaskPriority(self._priority.get()),
                "server_id": server_id,
            }
            self.destroy()

    class ServerDetailPanel(tk.Frame):
        """Panel showing details for a selected server."""

        def __init__(self, parent, **kwargs):
            super().__init__(parent, **kwargs)
            self._connection: Optional[ServerConnection] = None
            self._update_job = None
            self._build()

        def _build(self):
            # Header
            self._header_var = tk.StringVar(value="No server selected")
            tk.Label(self, textvariable=self._header_var, font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=4)

            # Metrics frame
            metrics_frame = tk.LabelFrame(self, text="Metrics")
            metrics_frame.pack(fill="x", padx=8, pady=4)

            self._cpu_var = tk.StringVar(value="CPU: --")
            self._ram_var = tk.StringVar(value="RAM: --")
            self._net_var = tk.StringVar(value="Net: --")
            self._status_var = tk.StringVar(value="Status: --")

            tk.Label(metrics_frame, textvariable=self._status_var).grid(row=0, column=0, sticky="w", padx=8)
            tk.Label(metrics_frame, textvariable=self._cpu_var).grid(row=0, column=1, sticky="w", padx=8)
            tk.Label(metrics_frame, textvariable=self._ram_var).grid(row=0, column=2, sticky="w", padx=8)
            tk.Label(metrics_frame, textvariable=self._net_var).grid(row=0, column=3, sticky="w", padx=8)

            # CPU history canvas
            hist_frame = tk.LabelFrame(self, text="CPU History (last 60s)")
            hist_frame.pack(fill="x", padx=8, pady=4)
            self._hist_canvas = tk.Canvas(hist_frame, height=60, bg="#1e1e1e")
            self._hist_canvas.pack(fill="x", padx=4, pady=4)

            # Process list
            proc_frame = tk.LabelFrame(self, text="Processes")
            proc_frame.pack(fill="both", expand=True, padx=8, pady=4)

            cols = ("PID", "Name", "CPU%", "RAM MB", "Status", "User")
            self._proc_tree = ttk.Treeview(proc_frame, columns=cols, show="headings", height=12)
            for col in cols:
                self._proc_tree.heading(col, text=col)
                self._proc_tree.column(col, width=90 if col != "Name" else 160)
            vsb = ttk.Scrollbar(proc_frame, orient="vertical", command=self._proc_tree.yview)
            self._proc_tree.configure(yscrollcommand=vsb.set)
            self._proc_tree.pack(side="left", fill="both", expand=True)
            vsb.pack(side="right", fill="y")

            # Kill button
            btn_frame = tk.Frame(self)
            btn_frame.pack(fill="x", padx=8, pady=4)
            tk.Button(btn_frame, text="Kill Selected Process", command=self._kill_process, bg="#c0392b", fg="white").pack(side="left")
            tk.Button(btn_frame, text="Refresh", command=self._refresh).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Screenshot", command=self._take_screenshot).pack(side="left", padx=4)

        def set_connection(self, conn: Optional[ServerConnection]) -> None:
            if self._update_job:
                self.after_cancel(self._update_job)
                self._update_job = None
            self._connection = conn
            if conn:
                self._header_var.set(f"Server: {conn.name} ({conn.config.host}:{conn.config.port})")
                self._schedule_update()
            else:
                self._header_var.set("No server selected")
                self._clear()

        def _clear(self):
            self._cpu_var.set("CPU: --")
            self._ram_var.set("RAM: --")
            self._net_var.set("Net: --")
            self._status_var.set("Status: --")
            for item in self._proc_tree.get_children():
                self._proc_tree.delete(item)

        def _schedule_update(self):
            self._update_ui()
            self._update_job = self.after(2000, self._schedule_update)

        def _update_ui(self):
            if not self._connection:
                return
            conn = self._connection
            self._status_var.set(f"Status: {conn.status.value}")
            metrics = conn.get_last_metrics()
            if metrics:
                self._cpu_var.set(f"CPU: {metrics.cpu_percent:.1f}%")
                self._ram_var.set(
                    f"RAM: {metrics.ram_used_mb:.0f}/{metrics.ram_total_mb:.0f} MB ({metrics.ram_percent:.1f}%)"
                )
                self._net_var.set(
                    f"Net ↑{metrics.net_bytes_sent // 1024}KB ↓{metrics.net_bytes_recv // 1024}KB"
                )
                self._update_history_canvas(conn.get_metrics_history())
                self._update_processes(metrics.processes)

        def _update_history_canvas(self, history: List[SystemMetrics]):
            canvas = self._hist_canvas
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 2 or not history:
                return
            recent = list(history)[-60:]
            n = len(recent)
            step = w / max(n, 1)
            points = []
            for i, m in enumerate(recent):
                x = i * step
                y = h - (m.cpu_percent / 100.0) * h
                points.extend([x, y])
            if len(points) >= 4:
                canvas.create_line(points, fill="#2ecc71", width=2)

        def _update_processes(self, processes: List[ProcessInfo]):
            for item in self._proc_tree.get_children():
                self._proc_tree.delete(item)
            sorted_procs = sorted(processes, key=lambda p: p.cpu_percent, reverse=True)
            for proc in sorted_procs[:100]:
                self._proc_tree.insert(
                    "",
                    "end",
                    values=(
                        proc.pid,
                        proc.name,
                        f"{proc.cpu_percent:.1f}",
                        f"{proc.memory_mb:.1f}",
                        proc.status,
                        proc.username,
                    ),
                )

        def _kill_process(self):
            if not self._connection:
                return
            sel = self._proc_tree.selection()
            if not sel:
                messagebox.showwarning("Warning", "Select a process first")
                return
            values = self._proc_tree.item(sel[0], "values")
            pid = int(values[0])
            name = values[1]
            if messagebox.askyesno("Confirm", f"Kill process {name} (PID {pid})?"):
                success, msg = self._connection.kill_process(pid)
                if success:
                    messagebox.showinfo("Success", msg)
                else:
                    messagebox.showerror("Error", msg)

        def _refresh(self):
            if self._connection and self._connection.status == ServerStatus.ONLINE:
                threading.Thread(target=self._connection.get_metrics, daemon=True).start()

        def _take_screenshot(self):
            if not self._connection:
                return
            if self._connection.status != ServerStatus.ONLINE:
                messagebox.showwarning("Warning", "Server is not online")
                return

            def _do():
                screenshot = self._connection.get_screenshot()
                if screenshot:
                    self.after(0, lambda: self._show_screenshot(screenshot))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "Failed to capture screenshot"))

            threading.Thread(target=_do, daemon=True).start()

        def _show_screenshot(self, b64_data: str):
            if Image is None:
                messagebox.showinfo("Screenshot", "PIL not available to display screenshot")
                return
            try:
                raw = base64.b64decode(b64_data)
                img = Image.open(io.BytesIO(raw))
                win = tk.Toplevel(self)
                win.title("Screenshot")
                photo = tk.PhotoImage(data=b64_data) if False else None
                # Use PIL ImageTk
                try:
                    from PIL import ImageTk
                    photo = ImageTk.PhotoImage(img)
                    lbl = tk.Label(win, image=photo)
                    lbl.image = photo
                    lbl.pack()
                except ImportError:
                    messagebox.showinfo("Screenshot", "ImageTk not available")
                    win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not display screenshot: {e}")

    class TaskPanel(tk.Frame):
        """Panel for managing tasks."""

        PRIORITY_COLORS = {
            TaskPriority.CRITICAL: "#e74c3c",
            TaskPriority.HIGH: "#e67e22",
            TaskPriority.MEDIUM: "#3498db",
            TaskPriority.LOW: "#95a5a6",
        }

        def __init__(self, parent, task_manager: TaskManager, server_manager: ServerManager, **kwargs):
            super().__init__(parent, **kwargs)
            self._tm = task_manager
            self._sm = server_manager
            self._build()
            self._refresh_tasks()

        def _build(self):
            btn_frame = tk.Frame(self)
            btn_frame.pack(fill="x", padx=8, pady=4)
            tk.Button(btn_frame, text="New Task", command=self._new_task, bg="#27ae60", fg="white").pack(side="left")
            tk.Button(btn_frame, text="Delete Task", command=self._delete_task, bg="#c0392b", fg="white").pack(side="left", padx=4)
            tk.Button(btn_frame, text="Mark Complete", command=self._mark_complete).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Refresh", command=self._refresh_tasks).pack(side="right")

            # Filter
            filter_frame = tk.Frame(self)
            filter_frame.pack(fill="x", padx=8)
            tk.Label(filter_frame, text="Filter by status:").pack(side="left")
            self._filter_var = tk.StringVar(value="all")
            statuses = ["all"] + [s.value for s in TaskStatus]
            ttk.Combobox(
                filter_frame,
                textvariable=self._filter_var,
                values=statuses,
                state="readonly",
                width=15,
            ).pack(side="left", padx=4)
            tk.Button(filter_frame, text="Apply", command=self._refresh_tasks).pack(side="left")

            # Task tree
            cols = ("Title", "Priority", "Status", "Server", "Created")
            self._tree = ttk.Treeview(self, columns=cols, show="headings")
            for col in cols:
                self._tree.heading(col, text=col)
                self._tree.column(col, width=120 if col != "Title" else 200)
            vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
            self._tree.configure(yscrollcommand=vsb.set)
            self._tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)
            vsb.pack(side="right", fill="y", pady=4, padx=(0, 8))

            self._task_ids: List[str] = []

        def _refresh_tasks(self):
            for item in self._tree.get_children():
                self._tree.delete(item)
            self._task_ids.clear()

            filter_val = self._filter_var.get()
            tasks = self._tm.get_all_tasks()
            if filter_val != "all":
                tasks = [t for t in tasks if t.status.value == filter_val]

            priority_order = {
                TaskPriority.CRITICAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3,
            }
            tasks.sort(key=lambda t: (priority_order.get(t.priority, 99), -t.created_at))

            servers = {s.server_id: s.name for s in self._sm.get_all_servers()}

            for task in tasks:
                created = datetime.fromtimestamp(task.created_at).strftime("%Y-%m-%d %H:%M")
                server_name = servers.get(task.server_id, task.server_id or "—")
                iid = self._tree.insert(
                    "",
                    "end",
                    values=(task.title, task.priority.value, task.status.value, server_name, created),
                )
                self._task_ids.append(task.task_id)

        def _get_selected_task_id(self) -> Optional[str]:
            sel = self._tree.selection()
            if not sel:
                return None
            idx = self._tree.index(sel[0])
            if idx < len(self._task_ids):
                return self._task_ids[idx]
            return None

        def _new_task(self):
            servers = self._sm.get_all_servers()
            dlg = AddTaskDialog(self, servers)
            self.wait_window(dlg)
            if dlg.result:
                r = dlg.result
                self._tm.create_task(
                    title=r["title"],
                    description=r["description"],
                    priority=r["priority"],
                    server_id=r["server_id"],
                )
                self._refresh_tasks()

        def _delete_task(self):
            task_id = self._get_selected_task_id()
            if not task_id:
                messagebox.showwarning("Warning", "Select a task first")
                return
            if messagebox.askyesno("Confirm", "Delete selected task?"):
                self._tm.delete_task(task_id)
                self._refresh_tasks()

        def _mark_complete(self):
            task_id = self._get_selected_task_id()
            if not task_id:
                messagebox.showwarning("Warning", "Select a task first")
                return
            self._tm.update_task(task_id, status=TaskStatus.COMPLETED)
            self._refresh_tasks()

    class NexusCtrlApp(tk.Tk):
        """Main application window."""

        def __init__(self):
            super().__init__()
            self.title("NexusCtrl - RDP Server Management")
            self.geometry("1200x750")
            self.configure(bg="#2c3e50")

            self._server_manager = ServerManager()
            self._task_manager = TaskManager()

            self._build_menu()
            self._build_ui()
            self._server_manager.connect_all()
            self._server_manager.start_monitoring_all()
            self._refresh_server_list()
            self._schedule_server_list_refresh()

        def _build_menu(self):
            menubar = tk.Menu(self)
            server_menu = tk.Menu(menubar, tearoff=0)
            server_menu.add_command(label="Add Server", command=self._add_server)
            server_menu.add_command(label="Remove Server", command=self._remove_server)
            server_menu.add_separator()
            server_menu.add_command(label="Connect All", command=self._connect_all)
            menubar.add_cascade(label="Servers", menu=server_menu)

            help_menu = tk.Menu(menubar, tearoff=0)
            help_menu.add_command(label="About", command=self._about)
            menubar.add_cascade(label="Help", menu=help_menu)
            self.config(menu=menubar)

        def _build_ui(self):
            # Main paned window
            paned = tk.PanedWindow(self, orient="horizontal", sashwidth=6, bg="#2c3e50")
            paned.pack(fill="both", expand=True)

            # Left panel: server list
            left_frame = tk.Frame(paned, bg="#34495e", width=220)
            paned.add(left_frame, minsize=180)

            tk.Label(left_frame, text="Servers", bg="#34495e", fg="white",
                     font=("Arial", 11, "bold")).pack(anchor="w", padx=8, pady=6)

            self._server_listbox = tk.Listbox(
                left_frame, bg="#2c3e50", fg="white", selectbackground="#2980b9",
                font=("Courier", 10), activestyle="none"
            )
            self._server_listbox.pack(fill="both", expand=True, padx=4, pady=4)
            self._server_listbox.bind("<<ListboxSelect>>", self._on_server_select)

            btn_frame = tk.Frame(left_frame, bg="#34495e")
            btn_frame.pack(fill="x", padx=4, pady=4)
            tk.Button(btn_frame, text="+", command=self._add_server, width=3, bg="#27ae60", fg="white").pack(side="left")
            tk.Button(btn_frame, text="−", command=self._remove_server, width=3, bg="#c0392b", fg="white").pack(side="left", padx=2)
            tk.Button(btn_frame, text="⟳", command=self._connect_selected, width=3).pack(side="left")

            # Right panel: notebook
            right_frame = tk.Frame(paned)
            paned.add(right_frame, minsize=600)

            notebook = ttk.Notebook(right_frame)
            notebook.pack(fill="both", expand=True)

            # Server detail tab
            self._detail_panel = ServerDetailPanel(notebook)
            notebook.add(self._detail_panel, text="Server Monitor")

            # Tasks tab
            self._task_panel = TaskPanel(notebook, self._task_manager, self._server_manager)
            notebook.add(self._task_panel, text="Tasks")

            # Log tab
            log_frame = tk.Frame(notebook)
            notebook.add(log_frame, text="Log")
            self._log_text = scrolledtext.ScrolledText(log_frame, state="disabled", bg="#1e1e1e", fg="#00ff00",
                                                        font=("Courier", 9))
            self._log_text.pack(fill="both", expand=True)

            self._server_ids: List[str] = []

        def _log(self, msg: str):
            ts = datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {msg}\n"
            self._log_text.configure(state="normal")
            self._log_text.insert(tk.END, line)
            self._log_text.see(tk.END)
            self._log_text.configure(state="disabled")

        def _refresh_server_list(self):
            self._server_listbox.delete(0, tk.END)
            self._server_ids.clear()
            for conn in self._server_manager.get_all_servers():
                status_icon = "●" if conn.status == ServerStatus.ONLINE else "○"
                self._server_listbox.insert(tk.END, f"{status_icon} {conn.name}")
                self._server_ids.append(conn.server_id)

        def _schedule_server_list_refresh(self):
            self._refresh_server_list()
            self.after(3000, self._schedule_server_list_refresh)

        def _on_server_select(self, event=None):
            sel = self._server_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx < len(self._server_ids):
                server_id = self._server_ids[idx]
                conn = self._server_manager.get_server(server_id)
                self._detail_panel.set_connection(conn)

        def _add_server(self):
            dlg = AddServerDialog(self)
            self.wait_window(dlg)
            if dlg.result:
                r = dlg.result
                cfg = self._server_manager.add_server(
                    name=r["name"],
                    host=r["host"],
                    port=r["port"],
                    description=r["description"],
                )
                self._log(f"Added server: {cfg.name} ({cfg.host}:{cfg.port})")
                conn = self._server_manager.get_server(cfg.server_id)
                if conn:
                    threading.Thread(target=conn.connect, daemon=True).start()
                    conn.start_monitoring()
                self._refresh_server_list()

        def _remove_server(self):
            sel = self._server_listbox.curselection()
            if not sel:
                messagebox.showwarning("Warning", "Select a server first")
                return
            idx = sel[0]
            if idx >= len(self._server_ids):
                return
            server_id = self._server_ids[idx]
            conn = self._server_manager.get_server(server_id)
            name = conn.name if conn else server_id
            if messagebox.askyesno("Confirm", f"Remove server '{name}'?"):
                self._server_manager.remove_server(server_id)
                self._detail_panel.set_connection(None)
                self._log(f"Removed server: {name}")
                self._refresh_server_list()

        def _connect_selected(self):
            sel = self._server_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(self._server_ids):
                return
            server_id = self._server_ids[idx]
            conn = self._server_manager.get_server(server_id)
            if conn:
                self._log(f"Connecting to {conn.name}...")
                threading.Thread(target=conn.connect, daemon=True).start()

        def _connect_all(self):
            self._log("Connecting to all servers...")
            self._server_manager.connect_all()

        def _about(self):
            messagebox.showinfo(
                "About NexusCtrl",
                "NexusCtrl - Personal RDP Server Management Tool\n\n"
                "Monitor and control multiple RDP servers.\n"
                "Features: real-time metrics, process management, task tracking.",
            )


# ─────────────────────────────────────────────
# CLI fallback
# ─────────────────────────────────────────────

class CLIController:
    """Simple CLI interface when Tkinter is not available."""

    def __init__(self):
        self._server_manager = ServerManager()
        self._task_manager = TaskManager()

    def run(self):
        print("NexusCtrl CLI Mode")
        print("Commands: list, add, connect, metrics, tasks, newtask, kill, quit")
        while True:
            try:
                cmd = input("\n> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "list":
                self._list_servers()
            elif cmd == "add":
                self._add_server()
            elif cmd == "connect":
                self._connect_server()
            elif cmd == "metrics":
                self._show_metrics()
            elif cmd == "tasks":
                self._list_tasks()
            elif cmd == "newtask":
                self._new_task()
            elif cmd == "kill":
                self._kill_process()
            elif cmd == "help":
                print("list, add, connect, metrics, tasks, newtask, kill, quit")
            else:
                print(f"Unknown command: {cmd}")

        self._server_manager.stop_monitoring_all()

    def _list_servers(self):
        servers = self._server_manager.get_all_servers()
        if not servers:
            print("No servers configured.")
            return
        for s in servers:
            print(f"  [{s.server_id}] {s.name} - {s.config.host}:{s.config.port} - {s.status.value}")

    def _add_server(self):
        name = input("Name: ").strip()
        host = input("Host: ").strip()
        port_str = input(f"Port [{Agent.DEFAULT_PORT}]: ").strip()
        port = int(port_str) if port_str else Agent.DEFAULT_PORT
        desc = input("Description: ").strip()
        cfg = self._server_manager.add_server(name, host, port, desc)
        print(f"Added server: {cfg.server_id}")

    def _connect_server(self):
        self._list_servers()
        server_id = input("Server ID: ").strip()
        conn = self._server_manager.get_server(server_id)
        if not conn:
            print("Server not found")
            return
        print(f"Connecting to {conn.name}...")
        if conn.connect():
            print("Connected!")
            conn.start_monitoring()
        else:
            print("Connection failed")

    def _show_metrics(self):
        self._list_servers()
        server_id = input("Server ID: ").strip()
        conn = self._server_manager.get_server(server_id)
        if not conn:
            print("Server not found")
            return
        if conn.status != ServerStatus.ONLINE:
            print("Server not online")
            return
        metrics = conn.get_metrics()
        if metrics:
            print(f"CPU: {metrics.cpu_percent:.1f}%")
            print(f"RAM: {metrics.ram_used_mb:.0f}/{metrics.ram_total_mb:.0f} MB ({metrics.ram_percent:.1f}%)")
            print(f"Net: ↑{metrics.net_bytes_sent // 1024}KB ↓{metrics.net_bytes_recv // 1024}KB")
            print(f"Processes ({len(metrics.processes)}):")
            for p in sorted(metrics.processes, key=lambda x: x.cpu_percent, reverse=True)[:10]:
                print(f"  PID={p.pid} {p.name} CPU={p.cpu_percent:.1f}% RAM={p.memory_mb:.1f}MB")
        else:
            print("Failed to get metrics")

    def _list_tasks(self):
        tasks = self._task_manager.get_all_tasks()
        if not tasks:
            print("No tasks.")
            return
        for t in tasks:
            print(f"  [{t.task_id}] [{t.priority.value}] {t.title} - {t.status.value}")

    def _new_task(self):
        title = input("Title: ").strip()
        desc = input("Description: ").strip()
        print("Priority: " + ", ".join(p.value for p in TaskPriority))
        priority_str = input("Priority [medium]: ").strip() or "medium"
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.MEDIUM
        task = self._task_manager.create_task(title, desc, priority)
        print(f"Created task: {task.task_id}")

    def _kill_process(self):
        self._list_servers()
        server_id = input("Server ID: ").strip()
        conn = self._server_manager.get_server(server_id)
        if not conn:
            print("Server not found")
            return
        pid_str = input("PID to kill: ").strip()
        try:
            pid = int(pid_str)
        except ValueError:
            print("Invalid PID")
            return
        success, msg = conn.kill_process(pid)
        print(f"{'Success' if success else 'Failed'}: {msg}")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "agent":
            host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
            port = int(sys.argv[3]) if len(sys.argv) > 3 else Agent.DEFAULT_PORT
            agent = Agent(host=host, port=port)
            agent.run_forever()
            return
        elif mode == "cli":
            cli = CLIController()
            cli.run()
            return

    if HAS_TK:
        app = NexusCtrlApp()
        app.mainloop()
    else:
        print("Tkinter not available, falling back to CLI mode")
        cli = CLIController()
        cli.run()


if __name__ == "__main__":
    main()