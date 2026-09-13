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
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

try:
    import psutil
except ImportError:
    psutil = None

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


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
    net_send_rate: float = 0.0
    net_recv_rate: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "net_bytes_sent": self.net_bytes_sent,
            "net_bytes_recv": self.net_bytes_recv,
            "net_send_rate": self.net_send_rate,
            "net_recv_rate": self.net_recv_rate,
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
        return cls(**d)


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    server_name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "server_name": self.server_name,
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
    name: str
    host: str
    port: int = 9999
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ServerConfig":
        return cls(**d)


# ─────────────────────────────────────────────
# Protocol helpers
# ─────────────────────────────────────────────

def send_message(sock: socket.socket, data: Dict[str, Any]) -> None:
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack(">I", len(payload))
    sock.sendall(header + payload)


def recv_message(sock: socket.socket) -> Optional[Dict[str, Any]]:
    raw_len = _recv_exact(sock, 4)
    if raw_len is None:
        return None
    msg_len = struct.unpack(">I", raw_len)[0]
    raw_data = _recv_exact(sock, msg_len)
    if raw_data is None:
        return None
    return json.loads(raw_data.decode("utf-8"))


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
    def __init__(self):
        self._prev_net = None
        self._prev_time = None

    def collect_metrics(self) -> SystemMetrics:
        if psutil is None:
            return SystemMetrics()

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        net = psutil.net_io_counters()
        now = time.time()

        send_rate = 0.0
        recv_rate = 0.0
        if self._prev_net is not None and self._prev_time is not None:
            dt = now - self._prev_time
            if dt > 0:
                send_rate = (net.bytes_sent - self._prev_net.bytes_sent) / dt
                recv_rate = (net.bytes_recv - self._prev_net.bytes_recv) / dt

        self._prev_net = net
        self._prev_time = now

        return SystemMetrics(
            cpu_percent=cpu,
            ram_percent=mem.percent,
            ram_used_mb=mem.used / (1024 * 1024),
            ram_total_mb=mem.total / (1024 * 1024),
            net_bytes_sent=net.bytes_sent,
            net_bytes_recv=net.bytes_recv,
            net_send_rate=send_rate,
            net_recv_rate=recv_rate,
            timestamp=now,
        )

    def collect_processes(self) -> List[ProcessInfo]:
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
        return procs

    def capture_screen(self) -> Optional[str]:
        if not PIL_AVAILABLE:
            return None
        try:
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=40)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

    def kill_process(self, pid: int) -> bool:
        if psutil is None:
            return False
        try:
            p = psutil.Process(pid)
            p.kill()
            return True
        except Exception:
            return False


class AgentClientHandler(threading.Thread):
    def __init__(self, conn: socket.socket, addr, collector: AgentMetricsCollector):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.collector = collector

    def run(self):
        print(f"[Agent] Connection from {self.addr}")
        try:
            while True:
                msg = recv_message(self.conn)
                if msg is None:
                    break
                self._handle(msg)
        except Exception as e:
            print(f"[Agent] Handler error: {e}")
        finally:
            self.conn.close()
            print(f"[Agent] Disconnected {self.addr}")

    def _handle(self, msg: Dict[str, Any]):
        cmd = msg.get("cmd")
        if cmd == "get_metrics":
            metrics = self.collector.collect_metrics()
            send_message(self.conn, {"type": "metrics", "data": metrics.to_dict()})
        elif cmd == "get_processes":
            procs = self.collector.collect_processes()
            send_message(self.conn, {"type": "processes", "data": [p.to_dict() for p in procs]})
        elif cmd == "get_screen":
            screen = self.collector.capture_screen()
            send_message(self.conn, {"type": "screen", "data": screen})
        elif cmd == "kill_process":
            pid = msg.get("pid")
            result = self.collector.kill_process(pid) if pid else False
            send_message(self.conn, {"type": "kill_result", "success": result, "pid": pid})
        else:
            send_message(self.conn, {"type": "error", "message": f"Unknown command: {cmd}"})


class Agent:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.collector = AgentMetricsCollector()
        self._running = False
        self._server_sock: Optional[socket.socket] = None

    def start(self):
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        print(f"[Agent] Listening on {self.host}:{self.port}")
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                handler = AgentClientHandler(conn, addr, self.collector)
                handler.start()
            except Exception as e:
                if self._running:
                    print(f"[Agent] Accept error: {e}")

    def stop(self):
        self._running = False
        if self._server_sock:
            self._server_sock.close()


# ─────────────────────────────────────────────
# Server Connection (controller side)
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
        self.last_screen: Optional[str] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._polling = False

    @property
    def name(self) -> str:
        return self.config.name

    def connect(self) -> bool:
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
            self.status = ServerStatus.CONNECTING
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((self.config.host, self.config.port))
                sock.settimeout(10)
                self._sock = sock
                self.status = ServerStatus.ONLINE
                return True
            except Exception as e:
                self.status = ServerStatus.OFFLINE
                self._sock = None
                return False

    def disconnect(self):
        self.stop_polling()
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.status = ServerStatus.OFFLINE

    def _send_recv(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._sock is None:
                return None
            try:
                send_message(self._sock, msg)
                return recv_message(self._sock)
            except Exception:
                self.status = ServerStatus.OFFLINE
                self._sock = None
                return None

    def fetch_metrics(self) -> Optional[SystemMetrics]:
        resp = self._send_recv({"cmd": "get_metrics"})
        if resp and resp.get("type") == "metrics":
            m = SystemMetrics.from_dict(resp["data"])
            self.last_metrics = m
            self.metrics_history.append(m)
            return m
        return None

    def fetch_processes(self) -> List[ProcessInfo]:
        resp = self._send_recv({"cmd": "get_processes"})
        if resp and resp.get("type") == "processes":
            procs = [ProcessInfo.from_dict(d) for d in resp["data"]]
            self.last_processes = procs
            return procs
        return []

    def fetch_screen(self) -> Optional[str]:
        resp = self._send_recv({"cmd": "get_screen"})
        if resp and resp.get("type") == "screen":
            self.last_screen = resp.get("data")
            return self.last_screen
        return None

    def kill_process(self, pid: int) -> bool:
        resp = self._send_recv({"cmd": "kill_process", "pid": pid})
        if resp and resp.get("type") == "kill_result":
            return resp.get("success", False)
        return False

    def start_polling(self, interval: float = 3.0):
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, args=(interval,), daemon=True)
        self._poll_thread.start()

    def stop_polling(self):
        self._polling = False

    def _poll_loop(self, interval: float):
        while self._polling:
            if self.status == ServerStatus.ONLINE:
                self.fetch_metrics()
                self.fetch_processes()
            elif self.status == ServerStatus.OFFLINE:
                self.connect()
            time.sleep(interval)


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
                for d in data:
                    t = Task.from_dict(d)
                    self._tasks[t.task_id] = t
            except Exception as e:
                print(f"[TaskManager] Load error: {e}")

    def _save(self):
        try:
            with open(self.storage_path, "w") as f:
                json.dump([t.to_dict() for t in self._tasks.values()], f, indent=2)
        except Exception as e:
            print(f"[TaskManager] Save error: {e}")

    def create_task(self, title: str, description: str, priority: TaskPriority,
                    server_name: str) -> Task:
        with self._lock:
            task_id = f"task_{int(time.time() * 1000)}_{len(self._tasks)}"
            task = Task(
                task_id=task_id,
                title=title,
                description=description,
                priority=priority,
                status=TaskStatus.PENDING,
                server_name=server_name,
            )
            self._tasks[task_id] = task
            self._save()
            return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            self._tasks[task_id].status = status
            self._tasks[task_id].updated_at = datetime.now().isoformat()
            self._save()
            return True

    def update_task(self, task_id: str, **kwargs) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            task = self._tasks[task_id]
            for k, v in kwargs.items():
                if hasattr(task, k):
                    setattr(task, k, v)
            task.updated_at = datetime.now().isoformat()
            self._save()
            return True

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            del self._tasks[task_id]
            self._save()
            return True

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def get_tasks_by_server(self, server_name: str) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.server_name == server_name]

    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.priority == priority]


# ─────────────────────────────────────────────
# Server Manager
# ─────────────────────────────────────────────

class ServerManager:
    def __init__(self, config_path: str = "servers.json"):
        self.config_path = config_path
        self._servers: Dict[str, ServerConnection] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                for d in data:
                    cfg = ServerConfig.from_dict(d)
                    conn = ServerConnection(cfg)
                    self._servers[cfg.name] = conn
            except Exception as e:
                print(f"[ServerManager] Load error: {e}")

    def _save(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump([s.config.to_dict() for s in self._servers.values()], f, indent=2)
        except Exception as e:
            print(f"[ServerManager] Save error: {e}")

    def add_server(self, config: ServerConfig) -> bool:
        with self._lock:
            if config.name in self._servers:
                return False
            conn = ServerConnection(config)
            self._servers[config.name] = conn
            self._save()
            return True

    def remove_server(self, name: str) -> bool:
        with self._lock:
            if name not in self._servers:
                return False
            self._servers[name].disconnect()
            del self._servers[name]
            self._save()
            return True

    def get_server(self, name: str) -> Optional[ServerConnection]:
        return self._servers.get(name)

    def get_all_servers(self) -> List[ServerConnection]:
        with self._lock:
            return list(self._servers.values())

    def connect_server(self, name: str) -> bool:
        server = self.get_server(name)
        if server is None:
            return False
        result = server.connect()
        if result:
            server.start_polling()
        return result

    def disconnect_server(self, name: str):
        server = self.get_server(name)
        if server:
            server.disconnect()

    def connect_all(self):
        for server in self.get_all_servers():
            t = threading.Thread(target=self.connect_server, args=(server.name,), daemon=True)
            t.start()

    def disconnect_all(self):
        for server in self.get_all_servers():
            server.disconnect()


# ─────────────────────────────────────────────
# GUI Application
# ─────────────────────────────────────────────

if TKINTER_AVAILABLE:

    class AddServerDialog(tk.Toplevel):
        def __init__(self, parent):
            super().__init__(parent)
            self.title("Add Server")
            self.resizable(False, False)
            self.result: Optional[ServerConfig] = None
            self._build()
            self.grab_set()

        def _build(self):
            pad = {"padx": 8, "pady": 4}
            tk.Label(self, text="Name:").grid(row=0, column=0, sticky="e", **pad)
            self._name = tk.Entry(self, width=25)
            self._name.grid(row=0, column=1, **pad)

            tk.Label(self, text="Host:").grid(row=1, column=0, sticky="e", **pad)
            self._host = tk.Entry(self, width=25)
            self._host.grid(row=1, column=1, **pad)

            tk.Label(self, text="Port:").grid(row=2, column=0, sticky="e", **pad)
            self._port = tk.Entry(self, width=25)
            self._port.insert(0, "9999")
            self._port.grid(row=2, column=1, **pad)

            tk.Label(self, text="Description:").grid(row=3, column=0, sticky="e", **pad)
            self._desc = tk.Entry(self, width=25)
            self._desc.grid(row=3, column=1, **pad)

            btn_frame = tk.Frame(self)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
            tk.Button(btn_frame, text="Add", command=self._on_add, width=10).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=4)

        def _on_add(self):
            name = self._name.get().strip()
            host = self._host.get().strip()
            port_str = self._port.get().strip()
            desc = self._desc.get().strip()
            if not name or not host:
                messagebox.showerror("Error", "Name and Host are required.", parent=self)
                return
            try:
                port = int(port_str)
            except ValueError:
                messagebox.showerror("Error", "Port must be a number.", parent=self)
                return
            self.result = ServerConfig(name=name, host=host, port=port, description=desc)
            self.destroy()


    class AddTaskDialog(tk.Toplevel):
        def __init__(self, parent, server_names: List[str]):
            super().__init__(parent)
            self.title("Add Task")
            self.resizable(False, False)
            self.result: Optional[Task] = None
            self._server_names = server_names
            self._build()
            self.grab_set()

        def _build(self):
            pad = {"padx": 8, "pady": 4}
            tk.Label(self, text="Title:").grid(row=0, column=0, sticky="e", **pad)
            self._title = tk.Entry(self, width=30)
            self._title.grid(row=0, column=1, **pad)

            tk.Label(self, text="Description:").grid(row=1, column=0, sticky="e", **pad)
            self._desc = tk.Text(self, width=30, height=4)
            self._desc.grid(row=1, column=1, **pad)

            tk.Label(self, text="Priority:").grid(row=2, column=0, sticky="e", **pad)
            self._priority = ttk.Combobox(self, values=[p.value for p in TaskPriority], state="readonly", width=27)
            self._priority.set(TaskPriority.MEDIUM.value)
            self._priority.grid(row=2, column=1, **pad)

            tk.Label(self, text="Server:").grid(row=3, column=0, sticky="e", **pad)
            self._server = ttk.Combobox(self, values=self._server_names or ["(none)"], state="readonly", width=27)
            if self._server_names:
                self._server.set(self._server_names[0])
            self._server.grid(row=3, column=1, **pad)

            btn_frame = tk.Frame(self)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=8)
            tk.Button(btn_frame, text="Create", command=self._on_create, width=10).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=4)

        def _on_create(self):
            title = self._title.get().strip()
            desc = self._desc.get("1.0", "end").strip()
            priority_str = self._priority.get()
            server = self._server.get()
            if not title:
                messagebox.showerror("Error", "Title is required.", parent=self)
                return
            self.result = {
                "title": title,
                "description": desc,
                "priority": TaskPriority(priority_str),
                "server_name": server,
            }
            self.destroy()


    class ServerDetailPanel(tk.Frame):
        def __init__(self, parent, server_manager: ServerManager):
            super().__init__(parent)
            self._server_manager = server_manager
            self._current_server: Optional[str] = None
            self._screen_update_id = None
            self._build()

        def _build(self):
            self._notebook = ttk.Notebook(self)
            self._notebook.pack(fill="both", expand=True)

            self._metrics_tab = tk.Frame(self._notebook)
            self._notebook.add(self._metrics_tab, text="Metrics")
            self._build_metrics_tab()

            self._processes_tab = tk.Frame(self._notebook)
            self._notebook.add(self._processes_tab, text="Processes")
            self._build_processes_tab()

            self._screen_tab = tk.Frame(self._notebook)
            self._notebook.add(self._screen_tab, text="Screen")
            self._build_screen_tab()

            self._history_tab = tk.Frame(self._notebook)
            self._notebook.add(self._history_tab, text="History")
            self._build_history_tab()

        def _build_metrics_tab(self):
            f = self._metrics_tab
            self._lbl_status = tk.Label(f, text="Status: --", font=("Arial", 11, "bold"))
            self._lbl_status.pack(anchor="w", padx=10, pady=5)
            self._lbl_cpu = tk.Label(f, text="CPU: --")
            self._lbl_cpu.pack(anchor="w", padx=10)
            self._lbl_ram = tk.Label(f, text="RAM: --")
            self._lbl_ram.pack(anchor="w", padx=10)
            self._lbl_net = tk.Label(f, text="Network: --")
            self._lbl_net.pack(anchor="w", padx=10)
            self._lbl_updated = tk.Label(f, text="Last updated: --", fg="gray")
            self._lbl_updated.pack(anchor="w", padx=10, pady=5)

            btn_frame = tk.Frame(f)
            btn_frame.pack(anchor="w", padx=10, pady=5)
            tk.Button(btn_frame, text="Refresh Metrics", command=self._refresh_metrics).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Connect", command=self._connect_server).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Disconnect", command=self._disconnect_server).pack(side="left", padx=4)

        def _build_processes_tab(self):
            f = self._processes_tab
            btn_frame = tk.Frame(f)
            btn_frame.pack(fill="x", padx=5, pady=5)
            tk.Button(btn_frame, text="Refresh Processes", command=self._refresh_processes).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Kill Selected", command=self._kill_selected_process).pack(side="left", padx=4)

            cols = ("PID", "Name", "CPU%", "Memory MB", "Status", "User")
            self._proc_tree = ttk.Treeview(f, columns=cols, show="headings", height=15)
            for col in cols:
                self._proc_tree.heading(col, text=col)
                self._proc_tree.column(col, width=100)
            self._proc_tree.column("Name", width=180)
            scrollbar = ttk.Scrollbar(f, orient="vertical", command=self._proc_tree.yview)
            self._proc_tree.configure(yscrollcommand=scrollbar.set)
            self._proc_tree.pack(side="left", fill="both", expand=True, padx=5)
            scrollbar.pack(side="right", fill="y")

        def _build_screen_tab(self):
            f = self._screen_tab
            btn_frame = tk.Frame(f)
            btn_frame.pack(fill="x", padx=5, pady=5)
            tk.Button(btn_frame, text="Capture Screen", command=self._capture_screen).pack(side="left", padx=4)
            self._auto_screen_var = tk.BooleanVar(value=False)
            tk.Checkbutton(btn_frame, text="Auto Refresh (5s)", variable=self._auto_screen_var,
                           command=self._toggle_auto_screen).pack(side="left", padx=4)

            self._screen_label = tk.Label(f, text="No screen capture", bg="black", fg="white")
            self._screen_label.pack(fill="both", expand=True, padx=5, pady=5)

        def _build_history_tab(self):
            f = self._history_tab
            tk.Label(f, text="Performance History (last 60 samples)").pack(anchor="w", padx=10, pady=5)
            self._history_text = scrolledtext.ScrolledText(f, height=20, state="disabled")
            self._history_text.pack(fill="both", expand=True, padx=5, pady=5)
            tk.Button(f, text="Refresh History", command=self._refresh_history).pack(anchor="w", padx=10, pady=5)

        def set_server(self, server_name: str):
            self._current_server = server_name
            self._refresh_metrics()
            self._refresh_processes()

        def _get_server(self) -> Optional[ServerConnection]:
            if self._current_server is None:
                return None
            return self._server_manager.get_server(self._current_server)

        def _refresh_metrics(self):
            server = self._get_server()
            if server is None:
                return
            status_color = {"online": "green", "offline": "red", "connecting": "orange", "error": "red"}
            color = status_color.get(server.status.value, "black")
            self._lbl_status.config(text=f"Status: {server.status.value.upper()}", fg=color)
            m = server.last_metrics
            if m:
                self._lbl_cpu.config(text=f"CPU: {m.cpu_percent:.1f}%")
                self._lbl_ram.config(text=f"RAM: {m.ram_used_mb:.0f} MB / {m.ram_total_mb:.0f} MB ({m.ram_percent:.1f}%)")
                self._lbl_net.config(text=f"Network: ↑ {m.net_send_rate/1024:.1f} KB/s  ↓ {m.net_recv_rate/1024:.1f} KB/s")
                self._lbl_updated.config(text=f"Last updated: {datetime.fromtimestamp(m.timestamp).strftime('%H:%M:%S')}")
            else:
                self._lbl_cpu.config(text="CPU: --")
                self._lbl_ram.config(text="RAM: --")
                self._lbl_net.config(text="Network: --")

        def _refresh_processes(self):
            server = self._get_server()
            if server is None:
                return
            procs = server.last_processes
            for item in self._proc_tree.get_children():
                self._proc_tree.delete(item)
            for p in sorted(procs, key=lambda x: x.cpu_percent, reverse=True):
                self._proc_tree.insert("", "end", values=(
                    p.pid, p.name, f"{p.cpu_percent:.1f}", f"{p.memory_mb:.1f}", p.status, p.username
                ))

        def _kill_selected_process(self):
            server = self._get_server()
            if server is None:
                return
            selected = self._proc_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Select a process first.")
                return
            item = self._proc_tree.item(selected[0])
            pid = int(item["values"][0])
            name = item["values"][1]
            if messagebox.askyesno("Confirm", f"Kill process {name} (PID {pid})?"):
                result = server.kill_process(pid)
                if result:
                    messagebox.showinfo("Success", f"Process {pid} killed.")
                    self._refresh_processes()
                else:
                    messagebox.showerror("Error", f"Failed to kill process {pid}.")

        def _capture_screen(self):
            server = self._get_server()
            if server is None:
                return
            screen_data = server.fetch_screen()
            self._display_screen(screen_data)

        def _display_screen(self, screen_data: Optional[str]):
            if screen_data is None:
                self._screen_label.config(image="", text="Screen capture not available")
                return
            try:
                from PIL import Image, ImageTk
                img_bytes = base64.b64decode(screen_data)
                img = Image.open(io.BytesIO(img_bytes))
                w, h = self._screen_label.winfo_width() or 640, self._screen_label.winfo_height() or 480
                img.thumbnail((max(w, 320), max(h, 240)), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._screen_label.config(image=photo, text="")
                self._screen_label._photo = photo
            except Exception:
                self._screen_label.config(image="", text="[Screen data received but PIL not available for display]")

        def _toggle_auto_screen(self):
            if self._auto_screen_var.get():
                self._schedule_auto_screen()
            else:
                if self._screen_update_id:
                    self.after_cancel(self._screen_update_id)
                    self._screen_update_id = None

        def _schedule_auto_screen(self):
            if self._auto_screen_var.get():
                self._capture_screen()
                self._screen_update_id = self.after(5000, self._schedule_auto_screen)

        def _refresh_history(self):
            server = self._get_server()
            if server is None:
                return
            self._history_text.config(state="normal")
            self._history_text.delete("1.0", "end")
            for m in server.metrics_history:
                ts = datetime.fromtimestamp(m.timestamp).strftime("%H:%M:%S")
                line = (f"[{ts}] CPU: {m.cpu_percent:.1f}%  "
                        f"RAM: {m.ram_percent:.1f}%  "
                        f"↑{m.net_send_rate/1024:.1f}KB/s  "
                        f"↓{m.net_recv_rate/1024:.1f}KB/s\n")
                self._history_text.insert("end", line)
            self._history_text.config(state="disabled")
            self._history_text.see("end")

        def _connect_server(self):
            if self._current_server:
                t = threading.Thread(
                    target=self._server_manager.connect_server,
                    args=(self._current_server,), daemon=True
                )
                t.start()

        def _disconnect_server(self):
            if self._current_server:
                self._server_manager.disconnect_server(self._current_server)
                self._refresh_metrics()


    class TaskPanel(tk.Frame):
        def __init__(self, parent, task_manager: TaskManager, server_manager: ServerManager):
            super().__init__(parent)
            self._task_manager = task_manager
            self._server_manager = server_manager
            self._build()
            self._refresh()

        def _build(self):
            btn_frame = tk.Frame(self)
            btn_frame.pack(fill="x", padx=5, pady=5)
            tk.Button(btn_frame, text="Add Task", command=self._add_task).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Delete Task", command=self._delete_task).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Mark Complete", command=self._mark_complete).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Mark In Progress", command=self._mark_in_progress).pack(side="left", padx=4)
            tk.Button(btn_frame, text="Refresh", command=self._refresh).pack(side="left", padx=4)

            filter_frame = tk.Frame(self)
            filter_frame.pack(fill="x", padx=5)
            tk.Label(filter_frame, text="Filter Priority:").pack(side="left")
            self._filter_priority = ttk.Combobox(filter_frame,
                                                  values=["All"] + [p.value for p in TaskPriority],
                                                  state="readonly", width=12)
            self._filter_priority.set("All")
            self._filter_priority.pack(side="left", padx=4)
            self._filter_priority.bind("<<ComboboxSelected>>", lambda e: self._refresh())

            tk.Label(filter_frame, text="Filter Status:").pack(side="left", padx=(10, 0))
            self._filter_status = ttk.Combobox(filter_frame,
                                                values=["All"] + [s.value for s in TaskStatus],
                                                state="readonly", width=12)
            self._filter_status.set("All")
            self._filter_status.pack(side="left", padx=4)
            self._filter_status.bind("<<ComboboxSelected>>", lambda e: self._refresh())

            cols = ("ID", "Title", "Priority", "Status", "Server", "Created")
            self._task_tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
            for col in cols:
                self._task_tree.heading(col, text=col)
                self._task_tree.column(col, width=100)
            self._task_tree.column("ID", width=60)
            self._task_tree.column("Title", width=200)
            self._task_tree.column("Created", width=150)

            scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._task_tree.yview)
            self._task_tree.configure(yscrollcommand=scrollbar.set)
            self._task_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            scrollbar.pack(side="right", fill="y")

            priority_colors = {
                "critical": "#ff4444",
                "high": "#ff8800",
                "medium": "#ffcc00",
                "low": "#88cc88",
            }
            for p, color in priority_colors.items():
                self._task_tree.tag_configure(p, background=color)

        def _refresh(self):
            tasks = self._task_manager.get_all_tasks()
            fp = self._filter_priority.get()
            fs = self._filter_status.get()
            if fp != "All":
                tasks = [t for t in tasks if t.priority.value == fp]
            if fs != "All":
                tasks = [t for t in tasks if t.status.value == fs]

            for item in self._task_tree.get_children():
                self._task_tree.delete(item)

            priority_order = {TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1,
                              TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}
            tasks.sort(key=lambda t: priority_order.get(t.priority, 99))

            for t in tasks:
                short_id = t.task_id.split("_")[-1]
                self._task_tree.insert("", "end", iid=t.task_id,
                                       values=(short_id, t.title, t.priority.value,
                                               t.status.value, t.server_name, t.created_at[:19]),
                                       tags=(t.priority.value,))

        def _add_task(self):
            server_names = [s.name for s in self._server_manager.get_all_servers()]
            dlg = AddTaskDialog(self, server_names)
            self.wait_window(dlg)
            if dlg.result:
                r = dlg.result
                self._task_manager.create_task(
                    title=r["title"],
                    description=r["description"],
                    priority=r["priority"],
                    server_name=r["server_name"],
                )
                self._refresh()

        def _delete_task(self):
            selected = self._task_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Select a task first.")
                return
            task_id = selected[0]
            if messagebox.askyesno("Confirm", "Delete selected task?"):
                self._task_manager.delete_task(task_id)
                self._refresh()

        def _mark_complete(self):
            selected = self._task_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Select a task first.")
                return
            self._task_manager.update_task_status(selected[0], TaskStatus.COMPLETED)
            self._refresh()

        def _mark_in_progress(self):
            selected = self._task_tree.selection()
            if not selected:
                messagebox.showinfo("Info", "Select a task first.")
                return
            self._task_manager.update_task_status(selected[0], TaskStatus.IN_PROGRESS)
            self._refresh()


    class NexusCtrlApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("NexusCtrl - RDP Server Management")
            self.geometry("1200x750")
            self.protocol("WM_DELETE_WINDOW", self._on_close)

            self._server_manager = ServerManager()
            self._task_manager = TaskManager()

            self._build_menu()
            self._build_ui()
            self._start_refresh_loop()

        def _build_menu(self):
            menubar = tk.Menu(self)
            self.config(menu=menubar)

            server_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Servers", menu=server_menu)
            server_menu.add_command(label="Add Server", command=self._add_server)
            server_menu.add_command(label="Remove Server", command=self._remove_server)
            server_menu.add_separator()
            server_menu.add_command(label="Connect All", command=self._connect_all)
            server_menu.add_command(label="Disconnect All", command=self._disconnect_all)

            task_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Tasks", menu=task_menu)
            task_menu.add_command(label="Add Task", command=self._add_task_from_menu)

        def _build_ui(self):
            paned = ttk.PanedWindow(self, orient="horizontal")
            paned.pack(fill="both", expand=True)

            left_frame = tk.Frame(paned, width=200)
            paned.add(left_frame, weight=0)

            tk.Label(left_frame, text="Servers", font=("Arial", 12, "bold")).pack(pady=5)
            self._server_listbox = tk.Listbox(left_frame, width=22, height=20)
            self._server_listbox.pack(fill="both", expand=True, padx=5, pady=5)
            self._server_listbox.bind("<<ListboxSelect>>", self._on_server_select)

            btn_frame = tk.Frame(left_frame)
            btn_frame.pack(fill="x", padx=5, pady=2)
            tk.Button(btn_frame, text="Add", command=self._add_server, width=8).pack(side="left")
            tk.Button(btn_frame, text="Remove", command=self._remove_server, width=8).pack(side="right")

            right_frame = tk.Frame(paned)
            paned.add(right_frame, weight=1)

            self._main_notebook = ttk.Notebook(right_frame)
            self._main_notebook.pack(fill="both", expand=True)

            self._server_detail = ServerDetailPanel(self._main_notebook, self._server_manager)
            self._main_notebook.add(self._server_detail, text="Server Detail")

            self._task_panel = TaskPanel(self._main_notebook, self._task_manager, self._server_manager)
            self._main_notebook.add(self._task_panel, text="Tasks")

            self._status_bar = tk.Label(self, text="Ready", bd=1, relief="sunken", anchor="w")
            self._status_bar.pack(side="bottom", fill="x")

            self._refresh_server_list()

        def _refresh_server_list(self):
            self._server_listbox.delete(0, "end")
            for server in self._server_manager.get_all_servers():
                status_icon = "●" if server.status == ServerStatus.ONLINE else "○"
                self._server_listbox.insert("end", f"{status_icon} {server.name}")

        def _on_server_select(self, event):
            selection = self._server_listbox.curselection()
            if not selection:
                return
            idx = selection[0]
            servers = self._server_manager.get_all_servers()
            if idx < len(servers):
                server = servers[idx]
                self._server_detail.set_server(server.name)
                self._main_notebook.select(0)

        def _add_server(self):
            dlg = AddServerDialog(self)
            self.wait_window(dlg)
            if dlg.result:
                if self._server_manager.add_server(dlg.result):
                    self._refresh_server_list()
                    self._set_status(f"Server '{dlg.result.name}' added.")
                else:
                    messagebox.showerror("Error", f"Server '{dlg.result.name}' already exists.")

        def _remove_server(self):
            selection = self._server_listbox.curselection()
            if not selection:
                messagebox.showinfo("Info", "Select a server first.")
                return
            idx = selection[0]
            servers = self._server_manager.get_all_servers()
            if idx < len(servers):
                name = servers[idx].name
                if messagebox.askyesno("Confirm", f"Remove server '{name}'?"):
                    self._server_manager.remove_server(name)
                    self._refresh_server_list()
                    self._set_status(f"Server '{name}' removed.")

        def _connect_all(self):
            self._server_manager.connect_all()
            self._set_status("Connecting to all servers...")

        def _disconnect_all(self):
            self._server_manager.disconnect_all()
            self._refresh_server_list()
            self._set_status("Disconnected from all servers.")

        def _add_task_from_menu(self):
            self._main_notebook.select(1)
            self._task_panel._add_task()

        def _set_status(self, msg: str):
            self._status_bar.config(text=msg)

        def _start_refresh_loop(self):
            self._refresh_server_list()
            self._server_detail._refresh_metrics()
            self.after(3000, self._start_refresh_loop)

        def _on_close(self):
            self._server_manager.disconnect_all()
            self.destroy()


# ─────────────────────────────────────────────
# CLI Entry Points
# ─────────────────────────────────────────────

def run_agent(host: str = "0.0.0.0", port: int = 9999):
    agent = Agent(host=host, port=port)
    print(f"Starting NexusCtrl Agent on {host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        agent.start()
    except KeyboardInterrupt:
        print("\nAgent stopped.")
        agent.stop()


def run_gui():
    if not TKINTER_AVAILABLE:
        print("Tkinter is not available. Cannot start GUI.")
        sys.exit(1)
    app = NexusCtrlApp()
    app.mainloop()


def run_cli_demo():
    print("NexusCtrl CLI Demo")
    print("=" * 40)

    sm = ServerManager("demo_servers.json")
    tm = TaskManager("demo_tasks.json")

    cfg = ServerConfig(name="demo-server", host="127.0.0.1", port=9999, description="Demo server")
    added = sm.add_server(cfg)
    print(f"Added server: {added}")

    t1 = tm.create_task("Setup monitoring", "Configure monitoring tools", TaskPriority.HIGH, "demo-server")
    t2 = tm.create_task("Update packages", "Run system updates", TaskPriority.MEDIUM, "demo-server")
    t3 = tm.create_task("Security audit", "Review security settings", TaskPriority.CRITICAL, "demo-server")

    print(f"\nCreated tasks:")
    for t in tm.get_all_tasks():
        print(f"  [{t.priority.value.upper()}] {t.title} - {t.status.value}")

    tm.update_task_status(t1.task_id, TaskStatus.IN_PROGRESS)
    tm.update_task_status(t2.task_id, TaskStatus.COMPLETED)

    print(f"\nUpdated tasks:")
    for t in tm.get_all_tasks():
        print(f"  [{t.priority.value.upper()}] {t.title} - {t.status.value}")

    print(f"\nServers:")
    for s in sm.get_all_servers():
        print(f"  {s.name} ({s.config.host}:{s.config.port}) - {s.status.value}")

    if psutil:
        collector = AgentMetricsCollector()
        metrics = collector.collect_metrics()
        print(f"\nLocal System Metrics:")
        print(f"  CPU: {metrics.cpu_percent:.1f}%")
        print(f"  RAM: {metrics.ram_used_mb:.0f} MB / {metrics.ram_total_mb:.0f} MB ({metrics.ram_percent:.1f}%)")
        print(f"  Net: ↑{metrics.net_send_rate/1024:.1f} KB/s  ↓{metrics.net_recv_rate/1024:.1f} KB/s")

        procs = collector.collect_processes()
        print(f"\nTop 5 Processes by CPU:")
        for p in sorted(procs, key=lambda x: x.cpu_percent, reverse=True)[:5]:
            print(f"  PID {p.pid:6d}  {p.name[:30]:30s}  CPU: {p.cpu_percent:.1f}%  MEM: {p.memory_mb:.1f} MB")
    else:
        print("\npsutil not available - skipping metrics collection")

    print("\nDemo complete.")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NexusCtrl - Personal RDP Server Management Tool")
    parser.add_argument("mode", nargs="?", default="gui",
                        choices=["gui", "agent", "demo"],
                        help="Run mode: gui (default), agent, or demo")
    parser.add_argument("--host", default="0.0.0.0", help="Agent bind host")
    parser.add_argument("--port", type=int, default=9999, help="Agent port")

    args = parser.parse_args()

    if args.mode == "agent":
        run_agent(host=args.host, port=args.port)
    elif args.mode == "demo":
        run_cli_demo()
    else:
        run_gui()