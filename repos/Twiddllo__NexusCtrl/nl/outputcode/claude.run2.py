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
    cmdline: str = ""


@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float
    net_bytes_sent: int
    net_bytes_recv: int
    processes: List[ProcessInfo] = field(default_factory=list)


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    server_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "server_id": self.server_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
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
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
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
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)


def recv_message(sock: socket.socket) -> Optional[Dict[str, Any]]:
    try:
        raw_len = _recv_exact(sock, 4)
        if raw_len is None:
            return None
        msg_len = struct.unpack("!I", raw_len)[0]
        raw_data = _recv_exact(sock, msg_len)
        if raw_data is None:
            return None
        return json.loads(raw_data.decode("utf-8"))
    except (json.JSONDecodeError, OSError):
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
    def __init__(self) -> None:
        self._prev_net = None

    def collect(self) -> Dict[str, Any]:
        if psutil is None:
            return {"error": "psutil not available"}

        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        net = psutil.net_io_counters()

        net_sent = net.bytes_sent
        net_recv = net.bytes_recv

        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username", "cmdline"]):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"] or "",
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / (1024 * 1024), 2),
                    "status": info["status"] or "",
                    "username": info["username"] or "",
                    "cmdline": " ".join(info["cmdline"] or [])[:200],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu,
            "ram_percent": mem.percent,
            "ram_used_mb": round(mem.used / (1024 * 1024), 2),
            "ram_total_mb": round(mem.total / (1024 * 1024), 2),
            "net_bytes_sent": net_sent,
            "net_bytes_recv": net_recv,
            "processes": processes,
        }

    def capture_screen(self) -> Optional[str]:
        if ImageGrab is None:
            return None
        try:
            img = ImageGrab.grab()
            img.thumbnail((1280, 720), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

    def kill_process(self, pid: int) -> Tuple[bool, str]:
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


class Agent:
    def __init__(self, host: str = "0.0.0.0", port: int = 9000) -> None:
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

    def _handle_client(self, conn: socket.socket) -> None:
        try:
            while True:
                msg = recv_message(conn)
                if msg is None:
                    break
                cmd = msg.get("command", "")
                if cmd == "get_metrics":
                    metrics = self.collector.collect()
                    send_message(conn, {"type": "metrics", "data": metrics})
                elif cmd == "get_screen":
                    screen_b64 = self.collector.capture_screen()
                    send_message(conn, {"type": "screen", "data": screen_b64})
                elif cmd == "kill_process":
                    pid = msg.get("pid")
                    if pid is not None:
                        ok, msg_text = self.collector.kill_process(int(pid))
                        send_message(conn, {"type": "kill_result", "success": ok, "message": msg_text})
                    else:
                        send_message(conn, {"type": "kill_result", "success": False, "message": "No PID provided"})
                elif cmd == "ping":
                    send_message(conn, {"type": "pong"})
                else:
                    send_message(conn, {"type": "error", "message": f"Unknown command: {cmd}"})
        except Exception as e:
            print(f"[Agent] Client error: {e}")
        finally:
            conn.close()

    def stop(self) -> None:
        self._running = False
        if self._server_sock:
            self._server_sock.close()


# ─────────────────────────────────────────────
# Server Connection (client side)
# ─────────────────────────────────────────────

class ServerConnection:
    HISTORY_MAX = 300

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.status = ServerStatus.OFFLINE
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self.metrics_history: deque = deque(maxlen=self.HISTORY_MAX)
        self.latest_metrics: Optional[SystemMetrics] = None
        self.latest_screen_b64: Optional[str] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False

    def connect(self) -> bool:
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
            try:
                self.status = ServerStatus.CONNECTING
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

    def disconnect(self) -> None:
        self._monitoring = False
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.status = ServerStatus.OFFLINE

    def _send_recv(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._sock is None:
                return None
            try:
                send_message(self._sock, command)
                return recv_message(self._sock)
            except Exception:
                self.status = ServerStatus.OFFLINE
                self._sock = None
                return None

    def ping(self) -> bool:
        resp = self._send_recv({"command": "ping"})
        return resp is not None and resp.get("type") == "pong"

    def get_metrics(self) -> Optional[SystemMetrics]:
        resp = self._send_recv({"command": "get_metrics"})
        if resp is None or resp.get("type") != "metrics":
            return None
        d = resp["data"]
        if "error" in d:
            return None
        procs = [
            ProcessInfo(
                pid=p["pid"],
                name=p["name"],
                cpu_percent=p["cpu_percent"],
                memory_mb=p["memory_mb"],
                status=p["status"],
                username=p.get("username", ""),
                cmdline=p.get("cmdline", ""),
            )
            for p in d.get("processes", [])
        ]
        metrics = SystemMetrics(
            timestamp=datetime.fromisoformat(d["timestamp"]),
            cpu_percent=d["cpu_percent"],
            ram_percent=d["ram_percent"],
            ram_used_mb=d["ram_used_mb"],
            ram_total_mb=d["ram_total_mb"],
            net_bytes_sent=d["net_bytes_sent"],
            net_bytes_recv=d["net_bytes_recv"],
            processes=procs,
        )
        self.latest_metrics = metrics
        self.metrics_history.append(metrics)
        return metrics

    def get_screen(self) -> Optional[str]:
        resp = self._send_recv({"command": "get_screen"})
        if resp is None or resp.get("type") != "screen":
            return None
        self.latest_screen_b64 = resp.get("data")
        return self.latest_screen_b64

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        resp = self._send_recv({"command": "kill_process", "pid": pid})
        if resp is None:
            return False, "No response from agent"
        return resp.get("success", False), resp.get("message", "")

    def start_monitoring(self, interval: float = 5.0) -> None:
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
            if self.status != ServerStatus.ONLINE:
                connected = self.connect()
                if not connected:
                    time.sleep(interval)
                    continue
            self.get_metrics()
            time.sleep(interval)

    def get_history_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": m.cpu_percent,
                "ram_percent": m.ram_percent,
                "net_bytes_sent": m.net_bytes_sent,
                "net_bytes_recv": m.net_bytes_recv,
            }
            for m in self.metrics_history
        ]


# ─────────────────────────────────────────────
# Task Manager
# ─────────────────────────────────────────────

class TaskManager:
    def __init__(self, storage_path: str = "tasks.json") -> None:
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
            now = datetime.now()
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
                if status == TaskStatus.COMPLETED and task.completed_at is None:
                    task.completed_at = datetime.now()
            if server_id is not None:
                task.server_id = server_id
            task.updated_at = datetime.now()
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
        tasks.sort(key=lambda t: (priority_order[t.priority], t.created_at))
        return tasks


# ─────────────────────────────────────────────
# Server Manager
# ─────────────────────────────────────────────

class ServerManager:
    def __init__(self, storage_path: str = "servers.json") -> None:
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

    def _generate_id(self) -> str:
        return f"srv_{int(time.time() * 1000)}_{len(self._configs)}"

    def add_server(self, name: str, host: str, port: int, description: str = "") -> ServerConfig:
        with self._lock:
            cfg = ServerConfig(
                server_id=self._generate_id(),
                name=name,
                host=host,
                port=port,
                description=description,
            )
            self._configs[cfg.server_id] = cfg
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

    def start_monitoring(self, server_id: str, interval: float = 5.0) -> bool:
        conn = self.get_connection(server_id)
        if conn is None:
            return False
        if conn.status != ServerStatus.ONLINE:
            if not conn.connect():
                return False
        conn.start_monitoring(interval)
        return True

    def stop_monitoring(self, server_id: str) -> None:
        conn = self._connections.get(server_id)
        if conn:
            conn.stop_monitoring()

    def get_all_statuses(self) -> Dict[str, ServerStatus]:
        result = {}
        for sid, cfg in self._configs.items():
            conn = self._connections.get(sid)
            result[sid] = conn.status if conn else ServerStatus.OFFLINE
        return result


# ─────────────────────────────────────────────
# NexusCtrl Core
# ─────────────────────────────────────────────

class NexusCtrl:
    def __init__(self) -> None:
        self.server_manager = ServerManager()
        self.task_manager = TaskManager()

    def add_server(self, name: str, host: str, port: int, description: str = "") -> ServerConfig:
        return self.server_manager.add_server(name, host, port, description)

    def remove_server(self, server_id: str) -> bool:
        return self.server_manager.remove_server(server_id)

    def connect(self, server_id: str) -> bool:
        return self.server_manager.connect_server(server_id)

    def disconnect(self, server_id: str) -> None:
        self.server_manager.disconnect_server(server_id)

    def start_monitoring(self, server_id: str, interval: float = 5.0) -> bool:
        return self.server_manager.start_monitoring(server_id, interval)

    def stop_monitoring(self, server_id: str) -> None:
        self.server_manager.stop_monitoring(server_id)

    def get_metrics(self, server_id: str) -> Optional[SystemMetrics]:
        conn = self.server_manager.get_connection(server_id)
        if conn is None:
            return None
        return conn.get_metrics()

    def get_screen(self, server_id: str) -> Optional[str]:
        conn = self.server_manager.get_connection(server_id)
        if conn is None:
            return None
        return conn.get_screen()

    def kill_process(self, server_id: str, pid: int) -> Tuple[bool, str]:
        conn = self.server_manager.get_connection(server_id)
        if conn is None:
            return False, "Server not found"
        return conn.kill_process(pid)

    def create_task(
        self,
        title: str,
        description: str,
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

    def list_servers(self) -> List[ServerConfig]:
        return self.server_manager.list_servers()

    def get_all_statuses(self) -> Dict[str, ServerStatus]:
        return self.server_manager.get_all_statuses()


# ─────────────────────────────────────────────
# GUI (Tkinter)
# ─────────────────────────────────────────────

if HAS_TK:
    class NexusCtrlGUI:
        REFRESH_INTERVAL_MS = 5000
        SCREEN_REFRESH_MS = 10000

        def __init__(self, root: tk.Tk, ctrl: NexusCtrl) -> None:
            self.root = root
            self.ctrl = ctrl
            self.root.title("NexusCtrl - RDP Server Management")
            self.root.geometry("1200x750")
            self.root.configure(bg="#1e1e2e")
            self._selected_server_id: Optional[str] = None
            self._screen_job: Optional[str] = None
            self._refresh_job: Optional[str] = None
            self._build_ui()
            self._refresh_server_list()
            self._schedule_refresh()

        # ── UI Build ──────────────────────────────

        def _build_ui(self) -> None:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
            style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                            padding=[10, 4], font=("Consolas", 10))
            style.map("TNotebook.Tab", background=[("selected", "#89b4fa")],
                      foreground=[("selected", "#1e1e2e")])
            style.configure("Treeview", background="#313244", foreground="#cdd6f4",
                            fieldbackground="#313244", rowheight=22, font=("Consolas", 9))
            style.configure("Treeview.Heading", background="#45475a", foreground="#cdd6f4",
                            font=("Consolas", 9, "bold"))
            style.map("Treeview", background=[("selected", "#89b4fa")],
                      foreground=[("selected", "#1e1e2e")])
            style.configure("TButton", background="#313244", foreground="#cdd6f4",
                            font=("Consolas", 9), borderwidth=0, padding=4)
            style.map("TButton", background=[("active", "#45475a")])
            style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4",
                            font=("Consolas", 9))
            style.configure("TEntry", fieldbackground="#313244", foreground="#cdd6f4",
                            insertcolor="#cdd6f4", font=("Consolas", 9))
            style.configure("TCombobox", fieldbackground="#313244", foreground="#cdd6f4",
                            font=("Consolas", 9))
            style.configure("TFrame", background="#1e1e2e")
            style.configure("TLabelframe", background="#1e1e2e", foreground="#89b4fa",
                            font=("Consolas", 9, "bold"))
            style.configure("TLabelframe.Label", background="#1e1e2e", foreground="#89b4fa")

            # Main paned window
            paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1e1e2e",
                                   sashwidth=4, sashrelief=tk.FLAT)
            paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

            # Left panel – server list
            left_frame = ttk.Frame(paned, width=220)
            paned.add(left_frame, minsize=180)
            self._build_server_panel(left_frame)

            # Right panel – notebook
            right_frame = ttk.Frame(paned)
            paned.add(right_frame, minsize=600)
            self._build_right_panel(right_frame)

        def _build_server_panel(self, parent: ttk.Frame) -> None:
            ttk.Label(parent, text="SERVERS", font=("Consolas", 10, "bold"),
                      foreground="#89b4fa").pack(pady=(8, 4))

            btn_frame = ttk.Frame(parent)
            btn_frame.pack(fill=tk.X, padx=4)
            ttk.Button(btn_frame, text="+ Add", command=self._add_server_dialog).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Remove", command=self._remove_server).pack(side=tk.LEFT, padx=2)
            ttk.Button(btn_frame, text="Connect", command=self._connect_server).pack(side=tk.LEFT, padx=2)

            self.server_listbox = tk.Listbox(
                parent, bg="#313244", fg="#cdd6f4", selectbackground="#89b4fa",
                selectforeground="#1e1e2e", font=("Consolas", 9), borderwidth=0,
                highlightthickness=0, activestyle="none"
            )
            self.server_listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self.server_listbox.bind("<<ListboxSelect>>", self._on_server_select)

            self._server_ids: List[str] = []

        def _build_right_panel(self, parent: ttk.Frame) -> None:
            self.notebook = ttk.Notebook(parent)
            self.notebook.pack(fill=tk.BOTH, expand=True)

            # Tab: Overview
            self.tab_overview = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_overview, text="Overview")
            self._build_overview_tab(self.tab_overview)

            # Tab: Processes
            self.tab_processes = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_processes, text="Processes")
            self._build_processes_tab(self.tab_processes)

            # Tab: Screen
            self.tab_screen = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_screen, text="Screen")
            self._build_screen_tab(self.tab_screen)

            # Tab: Tasks
            self.tab_tasks = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_tasks, text="Tasks")
            self._build_tasks_tab(self.tab_tasks)

            # Tab: History
            self.tab_history = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_history, text="History")
            self._build_history_tab(self.tab_history)

        def _build_overview_tab(self, parent: ttk.Frame) -> None:
            self.ov_status_var = tk.StringVar(value="No server selected")
            self.ov_cpu_var = tk.StringVar(value="CPU: --")
            self.ov_ram_var = tk.StringVar(value="RAM: --")
            self.ov_net_var = tk.StringVar(value="NET: --")

            info_frame = ttk.LabelFrame(parent, text="Server Info")
            info_frame.pack(fill=tk.X, padx=8, pady=8)

            ttk.Label(info_frame, textvariable=self.ov_status_var,
                      font=("Consolas", 10, "bold"), foreground="#a6e3a1").grid(
                row=0, column=0, columnspan=2, sticky=tk.W, padx=8, pady=4)

            metrics_frame = ttk.LabelFrame(parent, text="Live Metrics")
            metrics_frame.pack(fill=tk.X, padx=8, pady=4)

            for i, var in enumerate([self.ov_cpu_var, self.ov_ram_var, self.ov_net_var]):
                ttk.Label(metrics_frame, textvariable=var, font=("Consolas", 11),
                          foreground="#89dceb").grid(row=0, column=i, padx=20, pady=8)

            ctrl_frame = ttk.LabelFrame(parent, text="Controls")
            ctrl_frame.pack(fill=tk.X, padx=8, pady=4)
            ttk.Button(ctrl_frame, text="Refresh Metrics", command=self._manual_refresh).pack(
                side=tk.LEFT, padx=4, pady=4)
            ttk.Button(ctrl_frame, text="Start Monitoring", command=self._start_monitoring).pack(
                side=tk.LEFT, padx=4, pady=4)
            ttk.Button(ctrl_frame, text="Stop Monitoring", command=self._stop_monitoring).pack(
                side=tk.LEFT, padx=4, pady=4)
            ttk.Button(ctrl_frame, text="Disconnect", command=self._disconnect_server).pack(
                side=tk.LEFT, padx=4, pady=4)

            self.ov_log = scrolledtext.ScrolledText(
                parent, height=12, bg="#313244", fg="#cdd6f4",
                font=("Consolas", 8), state=tk.DISABLED, borderwidth=0
            )
            self.ov_log.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        def _build_processes_tab(self, parent: ttk.Frame) -> None:
            ctrl_frame = ttk.Frame(parent)
            ctrl_frame.pack(fill=tk.X, padx=8, pady=4)
            ttk.Button(ctrl_frame, text="Refresh", command=self._refresh_processes).pack(side=tk.LEFT, padx=4)
            ttk.Button(ctrl_frame, text="Kill Selected", command=self._kill_selected_process).pack(side=tk.LEFT, padx=4)

            cols = ("PID", "Name", "CPU%", "RAM(MB)", "Status", "User")
            self.proc_tree = ttk.Treeview(parent, columns=cols, show="headings", height=25)
            widths = [60, 200, 70, 80, 80, 100]
            for col, w in zip(cols, widths):
                self.proc_tree.heading(col, text=col)
                self.proc_tree.column(col, width=w, anchor=tk.W)

            vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.proc_tree.yview)
            self.proc_tree.configure(yscrollcommand=vsb.set)
            self.proc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
            vsb.pack(side=tk.LEFT, fill=tk.Y, pady=4)

        def _build_screen_tab(self, parent: ttk.Frame) -> None:
            ctrl_frame = ttk.Frame(parent)
            ctrl_frame.pack(fill=tk.X, padx=8, pady=4)
            ttk.Button(ctrl_frame, text="Capture Screen", command=self._capture_screen).pack(side=tk.LEFT, padx=4)
            self.screen_auto_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(ctrl_frame, text="Auto Refresh (10s)", variable=self.screen_auto_var,
                            command=self._toggle_screen_auto).pack(side=tk.LEFT, padx=4)

            self.screen_canvas = tk.Canvas(parent, bg="#181825", cursor="crosshair")
            self.screen_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
            self._screen_image_ref = None

        def _build_tasks_tab(self, parent: ttk.Frame) -> None:
            ctrl_frame = ttk.Frame(parent)
            ctrl_frame.pack(fill=tk.X, padx=8, pady=4)
            ttk.Button(ctrl_frame, text="New Task", command=self._new_task_dialog).pack(side=tk.LEFT, padx=4)
            ttk.Button(ctrl_frame, text="Edit Task", command=self._edit_task_dialog).pack(side=tk.LEFT, padx=4)
            ttk.Button(ctrl_frame, text="Delete Task", command=self._delete_task).pack(side=tk.LEFT, padx=4)
            ttk.Button(ctrl_frame, text="Mark Complete", command=self._mark_task_complete).pack(side=tk.LEFT, padx=4)
            ttk.Button(ctrl_frame, text="Refresh", command=self._refresh_tasks).pack(side=tk.LEFT, padx=4)

            filter_frame = ttk.Frame(parent)
            filter_frame.pack(fill=tk.X, padx=8, pady=2)
            ttk.Label(filter_frame, text="Filter Status:").pack(side=tk.LEFT)
            self.task_filter_var = tk.StringVar(value="all")
            status_cb = ttk.Combobox(filter_frame, textvariable=self.task_filter_var,
                                     values=["all", "pending", "in_progress", "completed", "cancelled"],
                                     width=12, state="readonly")
            status_cb.pack(side=tk.LEFT, padx=4)
            status_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_tasks())

            cols = ("ID", "Title", "Priority", "Status", "Server", "Created")
            self.task_tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
            widths = [120, 200, 80, 100, 120, 140]
            for col, w in zip(cols, widths):
                self.task_tree.heading(col, text=col)
                self.task_tree.column(col, width=w, anchor=tk.W)

            vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.task_tree.yview)
            self.task_tree.configure(yscrollcommand=vsb.set)
            self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
            vsb.pack(side=tk.LEFT, fill=tk.Y, pady=4)

            self._refresh_tasks()

        def _build_history_tab(self, parent: ttk.Frame) -> None:
            ttk.Label(parent, text="Performance History (last 300 samples)",
                      font=("Consolas", 9, "bold"), foreground="#89b4fa").pack(pady=4)

            cols = ("Timestamp", "CPU%", "RAM%", "Net Sent", "Net Recv")
            self.hist_tree = ttk.Treeview(parent, columns=cols, show="headings", height=28)
            widths = [160, 70, 70, 100, 100]
            for col, w in zip(cols, widths):
                self.hist_tree.heading(col, text=col)
                self.hist_tree.column(col, width=w, anchor=tk.W)

            vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.hist_tree.yview)
            self.hist_tree.configure(yscrollcommand=vsb.set)
            self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
            vsb.pack(side=tk.LEFT, fill=tk.Y, pady=4)

            ttk.Button(parent, text="Refresh History", command=self._refresh_history).pack(pady=4)

        # ── Server Panel Actions ──────────────────

        def _refresh_server_list(self) -> None:
            self.server_listbox.delete(0, tk.END)
            self._server_ids = []
            statuses = self.ctrl.get_all_statuses()
            for cfg in self.ctrl.list_servers():
                st = statuses.get(cfg.server_id, ServerStatus.OFFLINE)
                icon = "●" if st == ServerStatus.ONLINE else "○"
                color_tag = "online" if st == ServerStatus.ONLINE else "offline"
                self.server_listbox.insert(tk.END, f"{icon} {cfg.name} ({cfg.host}:{cfg.port})")
                self._server_ids.append(cfg.server_id)
            self.server_listbox.itemconfig(tk.END, fg="#a6e3a1")

        def _on_server_select(self, event: Any) -> None:
            sel = self.server_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx < len(self._server_ids):
                self._selected_server_id = self._server_ids[idx]
                cfg = self.ctrl.server_manager.get_server(self._selected_server_id)
                if cfg:
                    self.ov_status_var.set(f"{cfg.name} | {cfg.host}:{cfg.port}")
                self._manual_refresh()

        def _add_server_dialog(self) -> None:
            dlg = tk.Toplevel(self.root)
            dlg.title("Add Server")
            dlg.configure(bg="#1e1e2e")
            dlg.resizable(False, False)

            fields = [("Name", "My Server"), ("Host", "127.0.0.1"),
                      ("Port", "9000"), ("Description", "")]
            entries: Dict[str, tk.StringVar] = {}
            for i, (label, default) in enumerate(fields):
                ttk.Label(dlg, text=label + ":").grid(row=i, column=0, padx=8, pady=4, sticky=tk.W)
                var = tk.StringVar(value=default)
                ttk.Entry(dlg, textvariable=var, width=30).grid(row=i, column=1, padx=8, pady=4)
                entries[label] = var

            def do_add():
                try:
                    port = int(entries["Port"].get())
                except ValueError:
                    messagebox.showerror("Error", "Port must be a number", parent=dlg)
                    return
                self.ctrl.add_server(
                    entries["Name"].get(),
                    entries["Host"].get(),
                    port,
                    entries["Description"].get(),
                )
                self._refresh_server_list()
                dlg.destroy()

            ttk.Button(dlg, text="Add", command=do_add).grid(row=len(fields), column=0, columnspan=2, pady=8)

        def _remove_server(self) -> None:
            if not self._selected_server_id:
                return
            if messagebox.askyesno("Confirm", "Remove selected server?"):
                self.ctrl.remove_server(self._selected_server_id)
                self._selected_server_id = None
                self._refresh_server_list()

        def _connect_server(self) -> None:
            if not self._selected_server_id:
                messagebox.showinfo("Info", "Select a server first")
                return
            self._log(f"Connecting to server {self._selected_server_id}...")
            ok = self.ctrl.connect(self._selected_server_id)
            if ok:
                self._log("Connected successfully.")
                self._refresh_server_list()
            else:
                self._log("Connection failed.")
                messagebox.showerror("Error", "Could not connect to server")

        def _disconnect_server(self) -> None:
            if not self._selected_server_id:
                return
            self.ctrl.disconnect(self._selected_server_id)
            self._log("Disconnected.")
            self._refresh_server_list()

        def _start_monitoring(self) -> None:
            if not self._selected_server_id:
                return
            ok = self.ctrl.start_monitoring(self._selected_server_id)
            self._log("Monitoring started." if ok else "Failed to start monitoring.")

        def _stop_monitoring(self) -> None:
            if not self._selected_server_id:
                return
            self.ctrl.stop_monitoring(self._selected_server_id)
            self._log("Monitoring stopped.")

        # ── Overview ─────────────────────────────

        def _manual_refresh(self) -> None:
            if not self._selected_server_id:
                return
            conn = self.ctrl.server_manager.get_connection(self._selected_server_id)
            if conn is None:
                return
            if conn.status != ServerStatus.ONLINE:
                self._log("Server not connected.")
                return

            def fetch():
                metrics = self.ctrl.get_metrics(self._selected_server_id)
                if metrics:
                    self.root.after(0, lambda: self._update_overview(metrics))
                    self.root.after(0, self._refresh_processes)
                    self.root.after(0, self._refresh_history)
                else:
                    self.root.after(0, lambda: self._log("Failed to fetch metrics."))

            threading.Thread(target=fetch, daemon=True).start()

        def _update_overview(self, metrics: SystemMetrics) -> None:
            self.ov_cpu_var.set(f"CPU: {metrics.cpu_percent:.1f}%")
            self.ov_ram_var.set(
                f"RAM: {metrics.ram_percent:.1f}% ({metrics.ram_used_mb:.0f}/{metrics.ram_total_mb:.0f} MB)"
            )
            self.ov_net_var.set(
                f"NET ↑{self._fmt_bytes(metrics.net_bytes_sent)} ↓{self._fmt_bytes(metrics.net_bytes_recv)}"
            )
            self._log(
                f"[{metrics.timestamp.strftime('%H:%M:%S')}] "
                f"CPU={metrics.cpu_percent:.1f}% RAM={metrics.ram_percent:.1f}% "
                f"Procs={len(metrics.processes)}"
            )

        def _log(self, msg: str) -> None:
            self.ov_log.configure(state=tk.NORMAL)
            self.ov_log.insert(tk.END, msg + "\n")
            self.ov_log.see(tk.END)
            self.ov_log.configure(state=tk.DISABLED)

        def _fmt_bytes(self, b: int) -> str:
            for unit in ["B", "KB", "MB", "GB"]:
                if b < 1024:
                    return f"{b:.1f}{unit}"
                b /= 1024
            return f"{b:.1f}TB"

        # ── Processes ────────────────────────────

        def _refresh_processes(self) -> None:
            if not self._selected_server_id:
                return
            conn = self.ctrl.server_manager.get_connection(self._selected_server_id)
            if conn is None or conn.latest_metrics is None:
                return
            for row in self.proc_tree.get_children():
                self.proc_tree.delete(row)
            procs = sorted(conn.latest_metrics.processes, key=lambda p: p.cpu_percent, reverse=True)
            for p in procs:
                self.proc_tree.insert("", tk.END, values=(
                    p.pid, p.name, f"{p.cpu_percent:.1f}", f"{p.memory_mb:.1f}",
                    p.status, p.username
                ))

        def _kill_selected_process(self) -> None:
            if not self._selected_server_id:
                return
            sel = self.proc_tree.selection()
            if not sel:
                messagebox.showinfo("Info", "Select a process first")
                return
            item = self.proc_tree.item(sel[0])
            pid = int(item["values"][0])
            name = item["values"][1]
            if messagebox.askyesno("Confirm", f"Kill process {name} (PID {pid})?"):
                def do_kill():
                    ok, msg = self.ctrl.kill_process(self._selected_server_id, pid)
                    self.root.after(0, lambda: self._log(f"Kill {pid}: {msg}"))
                    if ok:
                        self.root.after(500, self._manual_refresh)

                threading.Thread(target=do_kill, daemon=True).start()

        # ── Screen ───────────────────────────────

        def _capture_screen(self) -> None:
            if not self._selected_server_id:
                return

            def fetch():
                b64 = self.ctrl.get_screen(self._selected_server_id)
                if b64:
                    self.root.after(0, lambda: self._display_screen(b64))
                else:
                    self.root.after(0, lambda: self._log("Screen capture failed or not available."))

            threading.Thread(target=fetch, daemon=True).start()

        def _display_screen(self, b64: str) -> None:
            if Image is None:
                self._log("Pillow not installed – cannot display screen.")
                return
            try:
                import tkinter.image
            except ImportError:
                pass
            try:
                from PIL import ImageTk
                data = base64.b64decode(b64)
                img = Image.open(io.BytesIO(data))
                cw = self.screen_canvas.winfo_width() or 800
                ch = self.screen_canvas.winfo_height() or 500
                img.thumbnail((cw, ch), Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(img)
                self.screen_canvas.delete("all")
                self.screen_canvas.create_image(cw // 2, ch // 2, anchor=tk.CENTER, image=photo)
                self._screen_image_ref = photo
            except Exception as e:
                self._log(f"Screen display error: {e}")

        def _toggle_screen_auto(self) -> None:
            if self.screen_auto_var.get():
                self._schedule_screen_refresh()
            else:
                if self._screen_job:
                    self.root.after_cancel(self._screen_job)
                    self._screen_job = None

        def _schedule_screen_refresh(self) -> None:
            if self.screen_auto_var.get():
                self._capture_screen()
                self._screen_job = self.root.after(self.SCREEN_REFRESH_MS, self._schedule_screen_refresh)

        # ── Tasks ────────────────────────────────

        def _refresh_tasks(self) -> None:
            for row in self.task_tree.get_children():
                self.task_tree.delete(row)
            fv = self.task_filter_var.get()
            status_filter = None if fv == "all" else TaskStatus(fv)
            tasks = self.ctrl.list_tasks(status=status_filter)
            priority_colors = {
                TaskPriority.CRITICAL: "#f38ba8",
                TaskPriority.HIGH: "#fab387",
                TaskPriority.MEDIUM: "#f9e2af",
                TaskPriority.LOW: "#a6e3a1",
            }
            for t in tasks:
                srv_name = ""
                if t.server_id:
                    cfg = self.ctrl.server_manager.get_server(t.server_id)
                    srv_name = cfg.name if cfg else t.server_id
                iid = self.task_tree.insert("", tk.END, values=(
                    t.task_id, t.title, t.priority.value, t.status.value,
                    srv_name, t.created_at.strftime("%Y-%m-%d %H:%M")
                ))
                self.task_tree.item(iid, tags=(t.priority.value,))
            for p, color in priority_colors.items():
                self.task_tree.tag_configure(p.value, foreground=color)

        def _new_task_dialog(self) -> None:
            self._task_dialog(None)

        def _edit_task_dialog(self) -> None:
            sel = self.task_tree.selection()
            if not sel:
                messagebox.showinfo("Info", "Select a task first")
                return
            task_id = self.task_tree.item(sel[0])["values"][0]
            task = self.ctrl.task_manager.get_task(task_id)
            if task:
                self._task_dialog(task)

        def _task_dialog(self, task: Optional[Task]) -> None:
            dlg = tk.Toplevel(self.root)
            dlg.title("Edit Task" if task else "New Task")
            dlg.configure(bg="#1e1e2e")
            dlg.resizable(False, False)

            ttk.Label(dlg, text="Title:").grid(row=0, column=0, padx=8, pady=4, sticky=tk.W)
            title_var = tk.StringVar(value=task.title if task else "")
            ttk.Entry(dlg, textvariable=title_var, width=40).grid(row=0, column=1, padx=8, pady=4)

            ttk.Label(dlg, text="Description:").grid(row=1, column=0, padx=8, pady=4, sticky=tk.W)
            desc_text = tk.Text(dlg, width=40, height=4, bg="#313244", fg="#cdd6f4",
                                font=("Consolas", 9), insertbackground="#cdd6f4")
            desc_text.grid(row=1, column=1, padx=8, pady=4)
            if task:
                desc_text.insert("1.0", task.description)

            ttk.Label(dlg, text="Priority:").grid(row=2, column=0, padx=8, pady=4, sticky=tk.W)
            prio_var = tk.StringVar(value=task.priority.value if task else "medium")
            ttk.Combobox(dlg, textvariable=prio_var,
                         values=[p.value for p in TaskPriority],
                         state="readonly", width=15).grid(row=2, column=1, padx=8, pady=4, sticky=tk.W)

            ttk.Label(dlg, text="Status:").grid(row=3, column=0, padx=8, pady=4, sticky=tk.W)
            status_var = tk.StringVar(value=task.status.value if task else "pending")
            ttk.Combobox(dlg, textvariable=status_var,
                         values=[s.value for s in TaskStatus],
                         state="readonly", width=15).grid(row=3, column=1, padx=8, pady=4, sticky=tk.W)

            ttk.Label(dlg, text="Server:").grid(row=4, column=0, padx=8, pady=4, sticky=tk.W)
            servers = self.ctrl.list_servers()
            srv_names = ["(none)"] + [f"{s.name} ({s.server_id})" for s in servers]
            srv_var = tk.StringVar(value="(none)")
            if task and task.server_id:
                cfg = self.ctrl.server_manager.get_server(task.server_id)
                if cfg:
                    srv_var.set(f"{cfg.name} ({cfg.server_id})")
            ttk.Combobox(dlg, textvariable=srv_var, values=srv_names,
                         state="readonly", width=30).grid(row=4, column=1, padx=8, pady=4, sticky=tk.W)

            def do_save():
                title = title_var.get().strip()
                if not title:
                    messagebox.showerror("Error", "Title is required", parent=dlg)
                    return
                desc = desc_text.get("1.0", tk.END).strip()
                priority = TaskPriority(prio_var.get())
                status = TaskStatus(status_var.get())
                srv_sel = srv_var.get()
                server_id = None
                if srv_sel != "(none)":
                    for s in servers:
                        if f"{s.name} ({s.server_id})" == srv_sel:
                            server_id = s.server_id
                            break
                if task:
                    self.ctrl.update_task(task.task_id, title=title, description=desc,
                                          priority=priority, status=status, server_id=server_id)
                else:
                    self.ctrl.create_task(title, desc, priority, server_id)
                self._refresh_tasks()
                dlg.destroy()

            ttk.Button(dlg, text="Save", command=do_save).grid(row=5, column=0, columnspan=2, pady=8)

        def _delete_task(self) -> None:
            sel = self.task_tree.selection()
            if not sel:
                return
            task_id = self.task_tree.item(sel[0])["values"][0]
            if messagebox.askyesno("Confirm", "Delete selected task?"):
                self.ctrl.delete_task(task_id)
                self._refresh_tasks()

        def _mark_task_complete(self) -> None:
            sel = self.task_tree.selection()
            if not sel:
                return
            task_id = self.task_tree.item(sel[0])["values"][0]
            self.ctrl.update_task(task_id, status=TaskStatus.COMPLETED)
            self._refresh_tasks()

        # ── History ──────────────────────────────

        def _refresh_history(self) -> None:
            if not self._selected_server_id:
                return
            conn = self.ctrl.server_manager.get_connection(self._selected_server_id)
            if conn is None:
                return
            for row in self.hist_tree.get_children():
                self.hist_tree.delete(row)
            history = conn.get_history_summary()
            for h in reversed(history):
                self.hist_tree.insert("", tk.END, values=(
                    h["timestamp"][:19],
                    f"{h['cpu_percent']:.1f}",
                    f"{h['ram_percent']:.1f}",
                    self._fmt_bytes(h["net_bytes_sent"]),
                    self._fmt_bytes(h["net_bytes_recv"]),
                ))

        # ── Periodic Refresh ─────────────────────

        def _schedule_refresh(self) -> None:
            self._refresh_server_list()
            if self._selected_server_id:
                conn = self.ctrl.server_manager.get_connection(self._selected_server_id)
                if conn and conn.latest_metrics:
                    self._update_overview(conn.latest_metrics)
                    self._refresh_processes()
                    self._refresh_history()
            self._refresh_job = self.root.after(self.REFRESH_INTERVAL_MS, self._schedule_refresh)


# ─────────────────────────────────────────────
# CLI fallback
# ─────────────────────────────────────────────

class NexusCtrlCLI:
    def __init__(self, ctrl: NexusCtrl) -> None:
        self.ctrl = ctrl

    def run(self) -> None:
        print("NexusCtrl CLI – type 'help' for commands")
        while True:
            try:
                line = input("nexus> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            try:
                self._dispatch(cmd, args)
            except Exception as e:
                print(f"Error: {e}")

    def _dispatch(self, cmd: str, args: List[str]) -> None:
        if cmd == "help":
            self._help()
        elif cmd == "servers":
            self._list_servers()
        elif cmd == "add-server":
            self._add_server(args)
        elif cmd == "remove-server":
            self._remove_server(args)
        elif cmd == "connect":
            self._connect(args)
        elif cmd == "disconnect":
            self._disconnect(args)
        elif cmd == "metrics":
            self._metrics(args)
        elif cmd == "processes":
            self._processes(args)
        elif cmd == "kill":
            self._kill(args)
        elif cmd == "tasks":
            self._list_tasks(args)
        elif cmd == "add-task":
            self._add_task(args)
        elif cmd == "complete-task":
            self._complete_task(args)
        elif cmd == "delete-task":
            self._delete_task(args)
        elif cmd == "monitor":
            self._monitor(args)
        elif cmd == "history":
            self._history(args)
        elif cmd in ("quit", "exit", "q"):
            raise SystemExit(0)
        else:
            print(f"Unknown command: {cmd}. Type 'help'.")

    def _help(self) -> None:
        help_text = """
Commands:
  servers                          List all servers
  add-server <name> <host> <port>  Add a server
  remove-server <id>               Remove a server
  connect <id>                     Connect to server
  disconnect <id>                  Disconnect from server
  metrics <id>                     Get live metrics
  processes <id>                   List processes
  kill <server_id> <pid>           Kill a process
  monitor <id> [interval]          Start background monitoring
  history <id>                     Show metrics history
  tasks [server_id]                List tasks
  add-task <title> [priority]      Add a task (priority: critical/high/medium/low)
  complete-task <task_id>          Mark task complete
  delete-task <task_id>            Delete a task
  quit                             Exit
"""
        print(help_text)

    def _list_servers(self) -> None:
        servers = self.ctrl.list_servers()
        statuses = self.ctrl.get_all_statuses()
        if not servers:
            print("No servers configured.")
            return
        print(f"{'ID':<25} {'Name':<20} {'Host':<20} {'Port':<6} {'Status'}")
        print("-" * 80)
        for s in servers:
            st = statuses.get(s.server_id, ServerStatus.OFFLINE).value
            print(f"{s.server_id:<25} {s.name:<20} {s.host:<20} {s.port:<6} {st}")

    def _add_server(self, args: List[str]) -> None:
        if len(args) < 3:
            print("Usage: add-server <name> <host> <port>")
            return
        name, host = args[0], args[1]
        try:
            port = int(args[2])
        except ValueError:
            print("Port must be an integer")
            return
        desc = " ".join(args[3:]) if len(args) > 3 else ""
        cfg = self.ctrl.add_server(name, host, port, desc)
        print(f"Added server: {cfg.server_id}")

    def _remove_server(self, args: List[str]) -> None:
        if not args:
            print("Usage: remove-server <id>")
            return
        ok = self.ctrl.remove_server(args[0])
        print("Removed." if ok else "Server not found.")

    def _connect(self, args: List[str]) -> None:
        if not args:
            print("Usage: connect <id>")
            return
        ok = self.ctrl.connect(args[0])
        print("Connected." if ok else "Connection failed.")

    def _disconnect(self, args: List[str]) -> None:
        if not args:
            print("Usage: disconnect <id>")
            return
        self.ctrl.disconnect(args[0])
        print("Disconnected.")

    def _metrics(self, args: List[str]) -> None:
        if not args:
            print("Usage: metrics <server_id>")
            return
        m = self.ctrl.get_metrics(args[0])
        if m is None:
            print("Failed to get metrics.")
            return
        print(f"Timestamp : {m.timestamp}")
        print(f"CPU       : {m.cpu_percent:.1f}%")
        print(f"RAM       : {m.ram_percent:.1f}% ({m.ram_used_mb:.0f}/{m.ram_total_mb:.0f} MB)")
        print(f"Net Sent  : {m.net_bytes_sent}")
        print(f"Net Recv  : {m.net_bytes_recv}")
        print(f"Processes : {len(m.processes)}")

    def _processes(self, args: List[str]) -> None:
        if not args:
            print("Usage: processes <server_id>")
            return
        m = self.ctrl.get_metrics(args[0])
        if m is None:
            print("Failed to get metrics.")
            return
        procs = sorted(m.processes, key=lambda p: p.cpu_percent, reverse=True)[:30]
        print(f"{'PID':<8} {'Name':<25} {'CPU%':<8} {'RAM(MB)':<10} {'Status':<12} {'User'}")
        print("-" * 80)
        for p in procs:
            print(f"{p.pid:<8} {p.name[:24]:<25} {p.cpu_percent:<8.1f} {p.memory_mb:<10.1f} {p.status:<12} {p.username}")

    def _kill(self, args: List[str]) -> None:
        if len(args) < 2:
            print("Usage: kill <server_id> <pid>")
            return
        try:
            pid = int(args[1])
        except ValueError:
            print("PID must be an integer")
            return
        ok, msg = self.ctrl.kill_process(args[0], pid)
        print(f"{'OK' if ok else 'FAIL'}: {msg}")

    def _monitor(self, args: List[str]) -> None:
        if not args:
            print("Usage: monitor <server_id> [interval_seconds]")
            return
        interval = float(args[1]) if len(args) > 1 else 5.0
        ok = self.ctrl.start_monitoring(args[0], interval)
        print(f"Monitoring {'started' if ok else 'failed'} (interval={interval}s)")

    def _history(self, args: List[str]) -> None:
        if not args:
            print("Usage: history <server_id>")
            return
        conn = self.ctrl.server_manager.get_connection(args[0])
        if conn is None:
            print("Server not found.")
            return
        history = conn.get_history_summary()
        if not history:
            print("No history available.")
            return
        print(f"{'Timestamp':<22} {'CPU%':<8} {'RAM%':<8} {'Net Sent':<14} {'Net Recv'}")
        print("-" * 70)
        for h in history[-20:]:
            print(f"{h['timestamp'][:19]:<22} {h['cpu_percent']:<8.1f} {h['ram_percent']:<8.1f} "
                  f"{h['net_bytes_sent']:<14} {h['net_bytes_recv']}")

    def _list_tasks(self, args: List[str]) -> None:
        server_id = args[0] if args else None
        tasks = self.ctrl.list_tasks(server_id=server_id)
        if not tasks:
            print("No tasks.")
            return
        print(f"{'ID':<25} {'Title':<25} {'Priority':<10} {'Status':<12} {'Server'}")
        print("-" * 90)
        for t in tasks:
            srv = t.server_id or ""
            print(f"{t.task_id:<25} {t.title[:24]:<25} {t.priority.value:<10} {t.status.value:<12} {srv}")

    def _add_task(self, args: List[str]) -> None:
        if not args:
            print("Usage: add-task <title> [priority]")
            return
        title = args[0]
        priority = TaskPriority.MEDIUM
        if len(args) > 1:
            try:
                priority = TaskPriority(args[1].lower())
            except ValueError:
                print(f"Invalid priority. Use: {[p.value for p in TaskPriority]}")
                return
        task = self.ctrl.create_task(title, "", priority)
        print(f"Created task: {task.task_id}")

    def _complete_task(self, args: List[str]) -> None:
        if not args:
            print("Usage: complete-task <task_id>")
            return
        t = self.ctrl.update_task(args[0], status=TaskStatus.COMPLETED)
        print("Task marked complete." if t else "Task not found.")

    def _delete_task(self, args: List[str]) -> None:
        if not args:
            print("Usage: delete-task <task_id>")
            return
        ok = self.ctrl.delete_task(args[0])
        print("Deleted." if ok else "Task not found.")


# ─────────────────────────────────────────────
# Entry Points
# ─────────────────────────────────────────────

def run_agent(host: str = "0.0.0.0", port: int = 9000) -> None:
    agent = Agent(host, port)
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
        print("[Agent] Stopped.")


def run_gui() -> None:
    if not HAS_TK:
        print("Tkinter not available. Falling back to CLI.")
        run_cli()
        return
    ctrl = NexusCtrl()
    root = tk.Tk()
    app = NexusCtrlGUI(root, ctrl)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


def run_cli() -> None:
    ctrl = NexusCtrl()
    cli = NexusCtrlCLI(ctrl)
    cli.run()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="NexusCtrl - RDP Server Management Tool")
    parser.add_argument("mode", nargs="?", default="gui",
                        choices=["gui", "cli", "agent"],
                        help="Run mode: gui (default), cli, or agent")
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