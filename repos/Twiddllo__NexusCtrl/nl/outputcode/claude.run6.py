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
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "net_bytes_sent": self.net_bytes_sent,
            "net_bytes_recv": self.net_bytes_recv,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemMetrics":
        obj = cls(
            cpu_percent=data.get("cpu_percent", 0.0),
            ram_percent=data.get("ram_percent", 0.0),
            ram_used_mb=data.get("ram_used_mb", 0.0),
            ram_total_mb=data.get("ram_total_mb", 0.0),
            net_bytes_sent=data.get("net_bytes_sent", 0),
            net_bytes_recv=data.get("net_bytes_recv", 0),
        )
        ts = data.get("timestamp")
        if ts:
            try:
                obj.timestamp = datetime.fromisoformat(ts)
            except Exception:
                pass
        return obj


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
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessInfo":
        return cls(
            pid=data.get("pid", 0),
            name=data.get("name", ""),
            cpu_percent=data.get("cpu_percent", 0.0),
            memory_mb=data.get("memory_mb", 0.0),
            status=data.get("status", ""),
            username=data.get("username", ""),
        )


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    priority: TaskPriority
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    server_id: Optional[str] = None

    def complete(self):
        self.completed = True
        self.completed_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "server_id": self.server_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        obj = cls(
            task_id=data["task_id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=TaskPriority(data.get("priority", "medium")),
            completed=data.get("completed", False),
            server_id=data.get("server_id"),
        )
        for attr, key in [("created_at", "created_at"), ("completed_at", "completed_at")]:
            val = data.get(key)
            if val:
                try:
                    setattr(obj, attr, datetime.fromisoformat(val))
                except Exception:
                    pass
        return obj


@dataclass
class ServerConfig:
    server_id: str
    name: str
    host: str
    port: int = 9999
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
            port=data.get("port", 9999),
            description=data.get("description", ""),
        )


# ─────────────────────────────────────────────
# Protocol helpers
# ─────────────────────────────────────────────

def send_message(sock: socket.socket, data: Dict[str, Any]) -> bool:
    try:
        payload = json.dumps(data).encode("utf-8")
        header = struct.pack("!I", len(payload))
        sock.sendall(header + payload)
        return True
    except Exception:
        return False


def recv_message(sock: socket.socket) -> Optional[Dict[str, Any]]:
    try:
        raw_len = _recv_exact(sock, 4)
        if raw_len is None:
            return None
        msg_len = struct.unpack("!I", raw_len)[0]
        if msg_len > 50 * 1024 * 1024:  # 50 MB safety cap
            return None
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

class Agent:
    """Runs as a background service on the target machine."""

    COLLECT_INTERVAL = 2  # seconds

    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._metrics_lock = threading.Lock()
        self._latest_metrics: Optional[SystemMetrics] = None
        self._latest_processes: List[ProcessInfo] = []
        self._collect_thread: Optional[threading.Thread] = None
        self._net_prev: Optional[Tuple[int, int]] = None

    # ── collection ──────────────────────────

    def _collect_metrics(self):
        while self._running:
            try:
                metrics = self._gather_metrics()
                processes = self._gather_processes()
                with self._metrics_lock:
                    self._latest_metrics = metrics
                    self._latest_processes = processes
            except Exception:
                pass
            time.sleep(self.COLLECT_INTERVAL)

    def _gather_metrics(self) -> SystemMetrics:
        if psutil is None:
            return SystemMetrics()
        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        net = psutil.net_io_counters()
        sent = net.bytes_sent
        recv = net.bytes_recv
        if self._net_prev is not None:
            delta_sent = max(0, sent - self._net_prev[0])
            delta_recv = max(0, recv - self._net_prev[1])
        else:
            delta_sent = 0
            delta_recv = 0
        self._net_prev = (sent, recv)
        return SystemMetrics(
            cpu_percent=cpu,
            ram_percent=vm.percent,
            ram_used_mb=vm.used / (1024 * 1024),
            ram_total_mb=vm.total / (1024 * 1024),
            net_bytes_sent=delta_sent,
            net_bytes_recv=delta_recv,
        )

    def _gather_processes(self) -> List[ProcessInfo]:
        if psutil is None:
            return []
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username"]):
            try:
                info = p.info
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
        procs.sort(key=lambda x: x.cpu_percent, reverse=True)
        return procs[:100]

    def _capture_screen(self) -> Optional[str]:
        if ImageGrab is None:
            return None
        try:
            img = ImageGrab.grab()
            img.thumbnail((1280, 720), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            return None

    def _kill_process(self, pid: int) -> Tuple[bool, str]:
        if psutil is None:
            return False, "psutil not available"
        try:
            p = psutil.Process(pid)
            p.terminate()
            return True, f"Process {pid} terminated"
        except psutil.NoSuchProcess:
            return False, f"Process {pid} not found"
        except psutil.AccessDenied:
            return False, f"Access denied for process {pid}"
        except Exception as e:
            return False, str(e)

    # ── networking ──────────────────────────

    def _handle_client(self, conn: socket.socket, addr):
        conn.settimeout(30)
        try:
            while self._running:
                msg = recv_message(conn)
                if msg is None:
                    break
                cmd = msg.get("cmd", "")
                response = self._dispatch(cmd, msg)
                if not send_message(conn, response):
                    break
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _dispatch(self, cmd: str, msg: Dict[str, Any]) -> Dict[str, Any]:
        if cmd == "get_metrics":
            with self._metrics_lock:
                m = self._latest_metrics
                procs = list(self._latest_processes)
            return {
                "status": "ok",
                "metrics": m.to_dict() if m else {},
                "processes": [p.to_dict() for p in procs],
            }
        elif cmd == "get_screen":
            img_b64 = self._capture_screen()
            return {"status": "ok", "image": img_b64}
        elif cmd == "kill_process":
            pid = msg.get("pid")
            if pid is None:
                return {"status": "error", "message": "No PID provided"}
            ok, message = self._kill_process(int(pid))
            return {"status": "ok" if ok else "error", "message": message}
        elif cmd == "ping":
            return {"status": "ok", "message": "pong"}
        else:
            return {"status": "error", "message": f"Unknown command: {cmd}"}

    def start(self):
        self._running = True
        self._collect_thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self._collect_thread.start()

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)
        print(f"[Agent] Listening on {self.host}:{self.port}")

        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def stop(self):
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass


# ─────────────────────────────────────────────
# ServerConnection (client side)
# ─────────────────────────────────────────────

class ServerConnection:
    """Manages a persistent connection to one agent."""

    HISTORY_SIZE = 60  # keep last 60 metric samples

    def __init__(self, config: ServerConfig):
        self.config = config
        self.status = ServerStatus.OFFLINE
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._metrics_history: deque = deque(maxlen=self.HISTORY_SIZE)
        self._latest_metrics: Optional[SystemMetrics] = None
        self._latest_processes: List[ProcessInfo] = []
        self._latest_screen: Optional[str] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._running = False

    # ── connection ──────────────────────────

    def connect(self) -> bool:
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.status = ServerStatus.CONNECTING
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.config.host, self.config.port))
            s.settimeout(10)
            with self._lock:
                self._sock = s
                self.status = ServerStatus.ONLINE
            return True
        except Exception:
            with self._lock:
                self.status = ServerStatus.OFFLINE
            return False

    def disconnect(self):
        self._running = False
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.status = ServerStatus.OFFLINE

    def _send_cmd(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            sock = self._sock
        if sock is None:
            return None
        try:
            if not send_message(sock, payload):
                self._mark_offline()
                return None
            resp = recv_message(sock)
            if resp is None:
                self._mark_offline()
            return resp
        except Exception:
            self._mark_offline()
            return None

    def _mark_offline(self):
        with self._lock:
            self.status = ServerStatus.OFFLINE
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None

    # ── polling ─────────────────────────────

    def start_polling(self, interval: float = 3.0):
        self._running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, args=(interval,), daemon=True
        )
        self._poll_thread.start()

    def _poll_loop(self, interval: float):
        while self._running:
            if self.status != ServerStatus.ONLINE:
                self.connect()
            if self.status == ServerStatus.ONLINE:
                self._fetch_metrics()
            time.sleep(interval)

    def _fetch_metrics(self):
        resp = self._send_cmd({"cmd": "get_metrics"})
        if resp and resp.get("status") == "ok":
            m = SystemMetrics.from_dict(resp.get("metrics", {}))
            procs = [ProcessInfo.from_dict(p) for p in resp.get("processes", [])]
            with self._lock:
                self._latest_metrics = m
                self._metrics_history.append(m)
                self._latest_processes = procs

    def fetch_screen(self) -> Optional[str]:
        resp = self._send_cmd({"cmd": "get_screen"})
        if resp and resp.get("status") == "ok":
            img = resp.get("image")
            with self._lock:
                self._latest_screen = img
            return img
        return None

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        resp = self._send_cmd({"cmd": "kill_process", "pid": pid})
        if resp is None:
            return False, "No response from agent"
        return resp.get("status") == "ok", resp.get("message", "")

    def ping(self) -> bool:
        resp = self._send_cmd({"cmd": "ping"})
        return resp is not None and resp.get("status") == "ok"

    # ── accessors ───────────────────────────

    @property
    def latest_metrics(self) -> Optional[SystemMetrics]:
        with self._lock:
            return self._latest_metrics

    @property
    def latest_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self._latest_processes)

    @property
    def metrics_history(self) -> List[SystemMetrics]:
        with self._lock:
            return list(self._metrics_history)

    @property
    def latest_screen(self) -> Optional[str]:
        with self._lock:
            return self._latest_screen


# ─────────────────────────────────────────────
# Task Manager
# ─────────────────────────────────────────────

class TaskManager:
    def __init__(self, storage_path: str = "tasks.json"):
        self.storage_path = storage_path
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                for item in data:
                    t = Task.from_dict(item)
                    self._tasks[t.task_id] = t
            except Exception:
                pass

    def _save(self):
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
        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            server_id=server_id,
        )
        with self._lock:
            self._tasks[task_id] = task
            self._save()
        return task

    def complete_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.complete()
            self._save()
        return True

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            del self._tasks[task_id]
            self._save()
        return True

    def get_all_tasks(self) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        tasks.sort(key=lambda t: (t.completed, priority_order.get(t.priority, 99)))
        return tasks

    def get_tasks_for_server(self, server_id: str) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.server_id == server_id]

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
    ) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if title is not None:
                task.title = title
            if description is not None:
                task.description = description
            if priority is not None:
                task.priority = priority
            self._save()
        return True


# ─────────────────────────────────────────────
# Server Manager (orchestrates connections)
# ─────────────────────────────────────────────

class ServerManager:
    def __init__(self, storage_path: str = "servers.json"):
        self.storage_path = storage_path
        self._configs: Dict[str, ServerConfig] = {}
        self._connections: Dict[str, ServerConnection] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                for item in data:
                    cfg = ServerConfig.from_dict(item)
                    self._configs[cfg.server_id] = cfg
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.storage_path, "w") as f:
                json.dump([c.to_dict() for c in self._configs.values()], f, indent=2)
        except Exception:
            pass

    def add_server(self, name: str, host: str, port: int = 9999, description: str = "") -> ServerConfig:
        server_id = f"srv_{int(time.time() * 1000)}"
        cfg = ServerConfig(server_id=server_id, name=name, host=host, port=port, description=description)
        with self._lock:
            self._configs[server_id] = cfg
            self._save()
        return cfg

    def remove_server(self, server_id: str) -> bool:
        with self._lock:
            if server_id not in self._configs:
                return False
            conn = self._connections.pop(server_id, None)
            if conn:
                conn.disconnect()
            del self._configs[server_id]
            self._save()
        return True

    def get_connection(self, server_id: str) -> Optional[ServerConnection]:
        with self._lock:
            if server_id not in self._configs:
                return None
            if server_id not in self._connections:
                cfg = self._configs[server_id]
                conn = ServerConnection(cfg)
                self._connections[server_id] = conn
            return self._connections[server_id]

    def connect_server(self, server_id: str, poll: bool = True) -> bool:
        conn = self.get_connection(server_id)
        if conn is None:
            return False
        ok = conn.connect()
        if ok and poll:
            conn.start_polling()
        return ok

    def disconnect_server(self, server_id: str):
        with self._lock:
            conn = self._connections.get(server_id)
        if conn:
            conn.disconnect()

    def get_all_configs(self) -> List[ServerConfig]:
        with self._lock:
            return list(self._configs.values())

    def get_config(self, server_id: str) -> Optional[ServerConfig]:
        with self._lock:
            return self._configs.get(server_id)

    def disconnect_all(self):
        with self._lock:
            conns = list(self._connections.values())
        for c in conns:
            c.disconnect()


# ─────────────────────────────────────────────
# GUI – NexusCtrl Dashboard
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
            self._port.insert(0, "9999")
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
            port_str = self._port.get().strip()
            if not name or not host:
                messagebox.showerror("Error", "Name and Host are required.", parent=self)
                return
            try:
                port = int(port_str)
            except ValueError:
                messagebox.showerror("Error", "Port must be a number.", parent=self)
                return
            self.result = {"name": name, "host": host, "port": port, "description": self._desc.get().strip()}
            self.destroy()

    class AddTaskDialog(tk.Toplevel):
        def __init__(self, parent, servers: List[ServerConfig]):
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

            tk.Label(self, text="Description:").grid(row=1, column=0, sticky="e", **pad)
            self._desc = tk.Text(self, width=35, height=4)
            self._desc.grid(row=1, column=1, **pad)

            tk.Label(self, text="Priority:").grid(row=2, column=0, sticky="e", **pad)
            self._priority = ttk.Combobox(self, values=["critical", "high", "medium", "low"], state="readonly", width=32)
            self._priority.set("medium")
            self._priority.grid(row=2, column=1, **pad)

            tk.Label(self, text="Server:").grid(row=3, column=0, sticky="e", **pad)
            server_names = ["(none)"] + [s.name for s in self._servers]
            self._server_var = tk.StringVar(value="(none)")
            self._server_cb = ttk.Combobox(self, textvariable=self._server_var, values=server_names, state="readonly", width=32)
            self._server_cb.grid(row=3, column=1, **pad)

            btn_frame = tk.Frame(self)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
            tk.Button(btn_frame, text="Create", command=self._ok, width=10).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=4)

        def _ok(self):
            title = self._title.get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required.", parent=self)
                return
            srv_name = self._server_var.get()
            server_id = None
            for s in self._servers:
                if s.name == srv_name:
                    server_id = s.server_id
                    break
            self.result = {
                "title": title,
                "description": self._desc.get("1.0", "end").strip(),
                "priority": self._priority.get(),
                "server_id": server_id,
            }
            self.destroy()

    class ServerDetailPanel(tk.Frame):
        """Shows metrics, processes, and screen for a selected server."""

        def __init__(self, parent, server_manager: "ServerManager"):
            super().__init__(parent, bg="#1e1e2e")
            self._sm = server_manager
            self._current_server_id: Optional[str] = None
            self._screen_update_job = None
            self._build()

        def _build(self):
            self._notebook = ttk.Notebook(self)
            self._notebook.pack(fill="both", expand=True)

            # ── Metrics tab ──
            self._metrics_frame = tk.Frame(self._notebook, bg="#1e1e2e")
            self._notebook.add(self._metrics_frame, text="Metrics")
            self._build_metrics_tab()

            # ── Processes tab ──
            self._proc_frame = tk.Frame(self._notebook, bg="#1e1e2e")
            self._notebook.add(self._proc_frame, text="Processes")
            self._build_processes_tab()

            # ── Screen tab ──
            self._screen_frame = tk.Frame(self._notebook, bg="#1e1e2e")
            self._notebook.add(self._screen_frame, text="Screen")
            self._build_screen_tab()

        def _build_metrics_tab(self):
            f = self._metrics_frame
            style_lbl = {"bg": "#1e1e2e", "fg": "#cdd6f4", "font": ("Consolas", 11)}

            self._lbl_cpu = tk.Label(f, text="CPU: --", **style_lbl)
            self._lbl_cpu.pack(anchor="w", padx=10, pady=4)

            self._cpu_bar = ttk.Progressbar(f, length=400, maximum=100)
            self._cpu_bar.pack(anchor="w", padx=10)

            self._lbl_ram = tk.Label(f, text="RAM: --", **style_lbl)
            self._lbl_ram.pack(anchor="w", padx=10, pady=4)

            self._ram_bar = ttk.Progressbar(f, length=400, maximum=100)
            self._ram_bar.pack(anchor="w", padx=10)

            self._lbl_net = tk.Label(f, text="Network: --", **style_lbl)
            self._lbl_net.pack(anchor="w", padx=10, pady=4)

            tk.Label(f, text="History (last 60 samples):", **style_lbl).pack(anchor="w", padx=10, pady=(12, 2))
            self._history_text = scrolledtext.ScrolledText(f, width=60, height=10, bg="#181825", fg="#a6e3a1",
                                                           font=("Consolas", 9))
            self._history_text.pack(padx=10, pady=4, fill="both", expand=True)

        def _build_processes_tab(self):
            f = self._proc_frame
            cols = ("PID", "Name", "CPU%", "RAM(MB)", "Status", "User")
            self._proc_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
            for col in cols:
                self._proc_tree.heading(col, text=col)
                self._proc_tree.column(col, width=100)
            self._proc_tree.column("Name", width=180)
            self._proc_tree.pack(fill="both", expand=True, padx=4, pady=4)

            sb = ttk.Scrollbar(f, orient="vertical", command=self._proc_tree.yview)
            self._proc_tree.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")

            btn_frame = tk.Frame(f, bg="#1e1e2e")
            btn_frame.pack(fill="x", padx=4, pady=4)
            tk.Button(btn_frame, text="Kill Selected Process", command=self._kill_selected,
                      bg="#f38ba8", fg="white").pack(side="left", padx=4)
            tk.Button(btn_frame, text="Refresh", command=self._refresh_processes,
                      bg="#89b4fa", fg="white").pack(side="left", padx=4)

        def _build_screen_tab(self):
            f = self._screen_frame
            self._screen_label = tk.Label(f, bg="#000000", text="No screen capture", fg="white")
            self._screen_label.pack(fill="both", expand=True)
            btn_frame = tk.Frame(f, bg="#1e1e2e")
            btn_frame.pack(fill="x")
            tk.Button(btn_frame, text="Capture Screen", command=self._capture_screen,
                      bg="#89b4fa", fg="white").pack(side="left", padx=4, pady=4)

        def load_server(self, server_id: str):
            self._current_server_id = server_id
            self.update_display()

        def update_display(self):
            if self._current_server_id is None:
                return
            conn = self._sm.get_connection(self._current_server_id)
            if conn is None:
                return
            self._update_metrics(conn)
            self._update_processes(conn)

        def _update_metrics(self, conn: ServerConnection):
            m = conn.latest_metrics
            if m is None:
                self._lbl_cpu.config(text="CPU: --")
                self._lbl_ram.config(text="RAM: --")
                self._lbl_net.config(text="Network: --")
                return
            self._lbl_cpu.config(text=f"CPU: {m.cpu_percent:.1f}%")
            self._cpu_bar["value"] = m.cpu_percent
            self._lbl_ram.config(text=f"RAM: {m.ram_percent:.1f}% ({m.ram_used_mb:.0f} MB / {m.ram_total_mb:.0f} MB)")
            self._ram_bar["value"] = m.ram_percent
            sent_kb = m.net_bytes_sent / 1024
            recv_kb = m.net_bytes_recv / 1024
            self._lbl_net.config(text=f"Network ↑ {sent_kb:.1f} KB/s  ↓ {recv_kb:.1f} KB/s")

            history = conn.metrics_history
            self._history_text.config(state="normal")
            self._history_text.delete("1.0", "end")
            for h in history[-20:]:
                line = (f"[{h.timestamp.strftime('%H:%M:%S')}] "
                        f"CPU:{h.cpu_percent:5.1f}%  RAM:{h.ram_percent:5.1f}%  "
                        f"↑{h.net_bytes_sent//1024:6}KB ↓{h.net_bytes_recv//1024:6}KB\n")
                self._history_text.insert("end", line)
            self._history_text.config(state="disabled")

        def _update_processes(self, conn: ServerConnection):
            procs = conn.latest_processes
            for item in self._proc_tree.get_children():
                self._proc_tree.delete(item)
            for p in procs:
                self._proc_tree.insert("", "end", values=(
                    p.pid, p.name, f"{p.cpu_percent:.1f}", f"{p.memory_mb:.1f}", p.status, p.username
                ))

        def _refresh_processes(self):
            if self._current_server_id is None:
                return
            conn = self._sm.get_connection(self._current_server_id)
            if conn:
                self._update_processes(conn)

        def _kill_selected(self):
            sel = self._proc_tree.selection()
            if not sel:
                messagebox.showinfo("Info", "Select a process first.")
                return
            item = self._proc_tree.item(sel[0])
            pid = int(item["values"][0])
            name = item["values"][1]
            if not messagebox.askyesno("Confirm", f"Kill process {name} (PID {pid})?"):
                return
            conn = self._sm.get_connection(self._current_server_id)
            if conn is None:
                return
            ok, msg = conn.kill_process(pid)
            if ok:
                messagebox.showinfo("Success", msg)
            else:
                messagebox.showerror("Error", msg)

        def _capture_screen(self):
            if self._current_server_id is None:
                return
            conn = self._sm.get_connection(self._current_server_id)
            if conn is None:
                return

            def _fetch():
                img_b64 = conn.fetch_screen()
                if img_b64 and Image:
                    try:
                        img_data = base64.b64decode(img_b64)
                        img = Image.open(io.BytesIO(img_data))
                        # Convert to PhotoImage
                        from PIL import ImageTk
                        photo = ImageTk.PhotoImage(img)
                        self._screen_label.config(image=photo, text="")
                        self._screen_label.image = photo  # keep reference
                    except Exception as e:
                        self._screen_label.config(text=f"Error: {e}", image="")
                else:
                    self._screen_label.config(text="Screen capture not available.", image="")

            threading.Thread(target=_fetch, daemon=True).start()

    class TaskPanel(tk.Frame):
        def __init__(self, parent, task_manager: TaskManager, server_manager: ServerManager):
            super().__init__(parent, bg="#1e1e2e")
            self._tm = task_manager
            self._sm = server_manager
            self._build()
            self.refresh()

        def _build(self):
            btn_frame = tk.Frame(self, bg="#1e1e2e")
            btn_frame.pack(fill="x", padx=4, pady=4)
            tk.Button(btn_frame, text="Add Task", command=self._add_task, bg="#a6e3a1", fg="black").pack(side="left", padx=4)
            tk.Button(btn_frame, text="Complete", command=self._complete_task, bg="#89b4fa", fg="white").pack(side="left", padx=4)
            tk.Button(btn_frame, text="Delete", command=self._delete_task, bg="#f38ba8", fg="white").pack(side="left", padx=4)
            tk.Button(btn_frame, text="Refresh", command=self.refresh, bg="#cba6f7", fg="white").pack(side="left", padx=4)

            cols = ("ID", "Title", "Priority", "Status", "Server", "Created")
            self._tree = ttk.Treeview(self, columns=cols, show="headings", height=25)
            for col in cols:
                self._tree.heading(col, text=col)
            self._tree.column("ID", width=80)
            self._tree.column("Title", width=200)
            self._tree.column("Priority", width=80)
            self._tree.column("Status", width=80)
            self._tree.column("Server", width=120)
            self._tree.column("Created", width=140)
            self._tree.pack(fill="both", expand=True, padx=4, pady=4)

            sb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
            self._tree.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")

        def refresh(self):
            for item in self._tree.get_children():
                self._tree.delete(item)
            tasks = self._tm.get_all_tasks()
            configs = {c.server_id: c.name for c in self._sm.get_all_configs()}
            for t in tasks:
                status = "Done" if t.completed else "Pending"
                srv_name = configs.get(t.server_id, "") if t.server_id else ""
                self._tree.insert("", "end", iid=t.task_id, values=(
                    t.task_id[-8:], t.title, t.priority.value, status,
                    srv_name, t.created_at.strftime("%Y-%m-%d %H:%M")
                ))

        def _add_task(self):
            dlg = AddTaskDialog(self, self._sm.get_all_configs())
            self.wait_window(dlg)
            if dlg.result:
                r = dlg.result
                self._tm.create_task(
                    title=r["title"],
                    description=r["description"],
                    priority=TaskPriority(r["priority"]),
                    server_id=r.get("server_id"),
                )
                self.refresh()

        def _complete_task(self):
            sel = self._tree.selection()
            if not sel:
                return
            task_id = sel[0]
            self._tm.complete_task(task_id)
            self.refresh()

        def _delete_task(self):
            sel = self._tree.selection()
            if not sel:
                return
            task_id = sel[0]
            if messagebox.askyesno("Confirm", "Delete this task?"):
                self._tm.delete_task(task_id)
                self.refresh()

    class NexusCtrlApp(tk.Tk):
        REFRESH_INTERVAL = 3000  # ms

        def __init__(self):
            super().__init__()
            self.title("NexusCtrl – RDP Server Management")
            self.geometry("1200x750")
            self.configure(bg="#1e1e2e")
            self._sm = ServerManager()
            self._tm = TaskManager()
            self._selected_server_id: Optional[str] = None
            self._build_ui()
            self._refresh_server_list()
            self._schedule_refresh()
            self.protocol("WM_DELETE_WINDOW", self._on_close)

        def _build_ui(self):
            # ── Left sidebar ──
            sidebar = tk.Frame(self, bg="#181825", width=220)
            sidebar.pack(side="left", fill="y")
            sidebar.pack_propagate(False)

            tk.Label(sidebar, text="NexusCtrl", bg="#181825", fg="#cba6f7",
                     font=("Consolas", 14, "bold")).pack(pady=10)
            tk.Label(sidebar, text="Servers", bg="#181825", fg="#a6adc8",
                     font=("Consolas", 10)).pack(anchor="w", padx=8)

            self._server_listbox = tk.Listbox(sidebar, bg="#313244", fg="#cdd6f4",
                                               selectbackground="#89b4fa", font=("Consolas", 10),
                                               height=15, borderwidth=0)
            self._server_listbox.pack(fill="x", padx=4, pady=4)
            self._server_listbox.bind("<<ListboxSelect>>", self._on_server_select)

            btn_frame = tk.Frame(sidebar, bg="#181825")
            btn_frame.pack(fill="x", padx=4)
            tk.Button(btn_frame, text="+ Add", command=self._add_server,
                      bg="#a6e3a1", fg="black", width=8).pack(side="left", padx=2, pady=2)
            tk.Button(btn_frame, text="Remove", command=self._remove_server,
                      bg="#f38ba8", fg="white", width=8).pack(side="left", padx=2, pady=2)
            tk.Button(btn_frame, text="Connect", command=self._connect_server,
                      bg="#89b4fa", fg="white", width=8).pack(side="left", padx=2, pady=2)

            self._status_label = tk.Label(sidebar, text="Status: --", bg="#181825", fg="#a6e3a1",
                                           font=("Consolas", 9), wraplength=200)
            self._status_label.pack(anchor="w", padx=8, pady=4)

            # ── Main area ──
            main = tk.Frame(self, bg="#1e1e2e")
            main.pack(side="left", fill="both", expand=True)

            self._notebook = ttk.Notebook(main)
            self._notebook.pack(fill="both", expand=True)

            # Server detail tab
            self._detail_panel = ServerDetailPanel(self._notebook, self._sm)
            self._notebook.add(self._detail_panel, text="Server Monitor")

            # Tasks tab
            self._task_panel = TaskPanel(self._notebook, self._tm, self._sm)
            self._notebook.add(self._task_panel, text="Tasks")

        def _refresh_server_list(self):
            self._server_listbox.delete(0, "end")
            self._server_configs = self._sm.get_all_configs()
            for cfg in self._server_configs:
                conn = self._sm.get_connection(cfg.server_id)
                status_icon = "🟢" if (conn and conn.status == ServerStatus.ONLINE) else "🔴"
                self._server_listbox.insert("end", f"{status_icon} {cfg.name} ({cfg.host}:{cfg.port})")

        def _on_server_select(self, event):
            sel = self._server_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(self._server_configs):
                return
            cfg = self._server_configs[idx]
            self._selected_server_id = cfg.server_id
            conn = self._sm.get_connection(cfg.server_id)
            status_str = conn.status.value if conn else "not connected"
            self._status_label.config(text=f"Status: {status_str}\n{cfg.host}:{cfg.port}")
            self._detail_panel.load_server(cfg.server_id)

        def _add_server(self):
            dlg = AddServerDialog(self)
            self.wait_window(dlg)
            if dlg.result:
                r = dlg.result
                self._sm.add_server(r["name"], r["host"], r["port"], r["description"])
                self._refresh_server_list()

        def _remove_server(self):
            if self._selected_server_id is None:
                messagebox.showinfo("Info", "Select a server first.")
                return
            if messagebox.askyesno("Confirm", "Remove this server?"):
                self._sm.remove_server(self._selected_server_id)
                self._selected_server_id = None
                self._refresh_server_list()

        def _connect_server(self):
            if self._selected_server_id is None:
                messagebox.showinfo("Info", "Select a server first.")
                return

            def _do_connect():
                ok = self._sm.connect_server(self._selected_server_id)
                msg = "Connected!" if ok else "Failed to connect."
                self._status_label.config(text=f"Status: {msg}")
                self._refresh_server_list()

            threading.Thread(target=_do_connect, daemon=True).start()

        def _schedule_refresh(self):
            self._refresh_server_list()
            if self._selected_server_id:
                self._detail_panel.update_display()
            self.after(self.REFRESH_INTERVAL, self._schedule_refresh)

        def _on_close(self):
            self._sm.disconnect_all()
            self.destroy()


# ─────────────────────────────────────────────
# CLI fallback
# ─────────────────────────────────────────────

class CLI:
    def __init__(self):
        self._sm = ServerManager()
        self._tm = TaskManager()

    def run(self):
        print("NexusCtrl CLI – type 'help' for commands")
        while True:
            try:
                line = input("nexus> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                self._sm.disconnect_all()
                break
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            self._dispatch(cmd, args)

    def _dispatch(self, cmd: str, args: List[str]):
        handlers = {
            "help": self._help,
            "list": self._list_servers,
            "add": self._add_server,
            "remove": self._remove_server,
            "connect": self._connect_server,
            "disconnect": self._disconnect_server,
            "metrics": self._show_metrics,
            "processes": self._show_processes,
            "kill": self._kill_process,
            "tasks": self._list_tasks,
            "addtask": self._add_task,
            "completetask": self._complete_task,
            "deletetask": self._delete_task,
            "exit": self._exit,
            "quit": self._exit,
        }
        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            print(f"Unknown command: {cmd}. Type 'help'.")

    def _help(self, args):
        print("""
Commands:
  list                        – List servers
  add <name> <host> [port]    – Add server
  remove <server_id>          – Remove server
  connect <server_id>         – Connect to server
  disconnect <server_id>      – Disconnect
  metrics <server_id>         – Show latest metrics
  processes <server_id>       – Show processes
  kill <server_id> <pid>      – Kill process
  tasks                       – List tasks
  addtask <title> [priority]  – Add task (priority: critical/high/medium/low)
  completetask <task_id>      – Mark task complete
  deletetask <task_id>        – Delete task
  exit / quit                 – Exit
""")

    def _list_servers(self, args):
        configs = self._sm.get_all_configs()
        if not configs:
            print("No servers configured.")
            return
        for cfg in configs:
            conn = self._sm.get_connection(cfg.server_id)
            status = conn.status.value if conn else "not connected"
            print(f"  [{cfg.server_id}] {cfg.name} – {cfg.host}:{cfg.port} – {status}")

    def _add_server(self, args):
        if len(args) < 2:
            print("Usage: add <name> <host> [port]")
            return
        name, host = args[0], args[1]
        port = int(args[2]) if len(args) > 2 else 9999
        cfg = self._sm.add_server(name, host, port)
        print(f"Added server: {cfg.server_id}")

    def _remove_server(self, args):
        if not args:
            print("Usage: remove <server_id>")
            return
        ok = self._sm.remove_server(args[0])
        print("Removed." if ok else "Server not found.")

    def _connect_server(self, args):
        if not args:
            print("Usage: connect <server_id>")
            return
        print(f"Connecting to {args[0]}...")
        ok = self._sm.connect_server(args[0])
        print("Connected." if ok else "Failed to connect.")

    def _disconnect_server(self, args):
        if not args:
            print("Usage: disconnect <server_id>")
            return
        self._sm.disconnect_server(args[0])
        print("Disconnected.")

    def _show_metrics(self, args):
        if not args:
            print("Usage: metrics <server_id>")
            return
        conn = self._sm.get_connection(args[0])
        if conn is None:
            print("Server not found.")
            return
        m = conn.latest_metrics
        if m is None:
            print("No metrics available. Is the server connected?")
            return
        print(f"CPU: {m.cpu_percent:.1f}%")
        print(f"RAM: {m.ram_percent:.1f}% ({m.ram_used_mb:.0f} MB / {m.ram_total_mb:.0f} MB)")
        print(f"Net ↑ {m.net_bytes_sent//1024} KB/s  ↓ {m.net_bytes_recv//1024} KB/s")

    def _show_processes(self, args):
        if not args:
            print("Usage: processes <server_id>")
            return
        conn = self._sm.get_connection(args[0])
        if conn is None:
            print("Server not found.")
            return
        procs = conn.latest_processes
        if not procs:
            print("No process data available.")
            return
        print(f"{'PID':>7}  {'CPU%':>6}  {'RAM(MB)':>8}  {'Status':>10}  Name")
        for p in procs[:30]:
            print(f"{p.pid:>7}  {p.cpu_percent:>6.1f}  {p.memory_mb:>8.1f}  {p.status:>10}  {p.name}")

    def _kill_process(self, args):
        if len(args) < 2:
            print("Usage: kill <server_id> <pid>")
            return
        conn = self._sm.get_connection(args[0])
        if conn is None:
            print("Server not found.")
            return
        ok, msg = conn.kill_process(int(args[1]))
        print(msg)

    def _list_tasks(self, args):
        tasks = self._tm.get_all_tasks()
        if not tasks:
            print("No tasks.")
            return
        for t in tasks:
            status = "✓" if t.completed else "○"
            print(f"  [{t.task_id[-8:]}] {status} [{t.priority.value:8}] {t.title}")

    def _add_task(self, args):
        if not args:
            print("Usage: addtask <title> [priority]")
            return
        title = args[0]
        priority = TaskPriority(args[1]) if len(args) > 1 else TaskPriority.MEDIUM
        task = self._tm.create_task(title=title, priority=priority)
        print(f"Task created: {task.task_id}")

    def _complete_task(self, args):
        if not args:
            print("Usage: completetask <task_id_suffix>")
            return
        # find by suffix
        tasks = self._tm.get_all_tasks()
        for t in tasks:
            if t.task_id.endswith(args[0]) or t.task_id == args[0]:
                self._tm.complete_task(t.task_id)
                print("Task completed.")
                return
        print("Task not found.")

    def _delete_task(self, args):
        if not args:
            print("Usage: deletetask <task_id_suffix>")
            return
        tasks = self._tm.get_all_tasks()
        for t in tasks:
            if t.task_id.endswith(args[0]) or t.task_id == args[0]:
                self._tm.delete_task(t.task_id)
                print("Task deleted.")
                return
        print("Task not found.")

    def _exit(self, args):
        print("Exiting.")
        self._sm.disconnect_all()
        sys.exit(0)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NexusCtrl – RDP Server Management Tool")
    parser.add_argument("--agent", action="store_true", help="Run as agent on this machine")
    parser.add_argument("--host", default="0.0.0.0", help="Agent bind host")
    parser.add_argument("--port", type=int, default=9999, help="Agent port")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode")
    args = parser.parse_args()

    if args.agent:
        agent = Agent(host=args.host, port=args.port)
        try:
            agent.start()
        except KeyboardInterrupt:
            print("\n[Agent] Stopping.")
            agent.stop()
        return

    if args.cli or not HAS_TK:
        cli = CLI()
        cli.run()
    else:
        app = NexusCtrlApp()
        app.mainloop()


if __name__ == "__main__":
    main()