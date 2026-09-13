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

    def to_dict(self) -> Dict:
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
    def from_dict(cls, data: Dict) -> "Task":
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

    def to_dict(self) -> Dict:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ServerConfig":
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

def send_message(sock: socket.socket, data: Dict) -> None:
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack(">I", len(payload))
    sock.sendall(header + payload)


def recv_message(sock: socket.socket) -> Optional[Dict]:
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
            if not chunk:
                return None
            data += chunk
        except Exception:
            return None
    return data


# ─────────────────────────────────────────────
# Agent (runs on target machine)
# ─────────────────────────────────────────────

class NexusAgent:
    """Runs as a background service on target machines."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._clients: List[socket.socket] = []
        self._lock = threading.Lock()

    # ── collection helpers ──────────────────

    def collect_metrics(self) -> Dict:
        if psutil is None:
            return {"error": "psutil not available"}
        cpu = psutil.cpu_percent(interval=0.5)
        vm = psutil.virtual_memory()
        net = psutil.net_io_counters()
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username", "cmdline"]):
            try:
                info = p.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"] or "",
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / 1024 / 1024, 2),
                    "status": info["status"] or "",
                    "username": info["username"] or "",
                    "cmdline": " ".join(info["cmdline"] or [])[:200],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {
            "type": "metrics",
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu,
            "ram_percent": vm.percent,
            "ram_used_mb": round(vm.used / 1024 / 1024, 2),
            "ram_total_mb": round(vm.total / 1024 / 1024, 2),
            "net_bytes_sent": net.bytes_sent,
            "net_bytes_recv": net.bytes_recv,
            "processes": procs,
        }

    def capture_screen(self) -> Optional[str]:
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

    def kill_process(self, pid: int) -> Dict:
        if psutil is None:
            return {"success": False, "error": "psutil not available"}
        try:
            p = psutil.Process(pid)
            p.terminate()
            return {"success": True, "pid": pid}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied for process {pid}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── networking ──────────────────────────

    def start(self) -> None:
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        print(f"[Agent] Listening on {self.host}:{self.port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()

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
                self._server_sock.settimeout(1.0)
                conn, addr = self._server_sock.accept()
                print(f"[Agent] Connection from {addr}")
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_client(self, conn: socket.socket) -> None:
        with self._lock:
            self._clients.append(conn)
        try:
            while self._running:
                msg = recv_message(conn)
                if msg is None:
                    break
                response = self._process_command(msg)
                if response:
                    send_message(conn, response)
        except Exception:
            pass
        finally:
            with self._lock:
                if conn in self._clients:
                    self._clients.remove(conn)
            try:
                conn.close()
            except Exception:
                pass

    def _process_command(self, msg: Dict) -> Optional[Dict]:
        cmd = msg.get("command")
        if cmd == "get_metrics":
            return self.collect_metrics()
        elif cmd == "get_screen":
            screen_b64 = self.capture_screen()
            return {"type": "screen", "data": screen_b64}
        elif cmd == "kill_process":
            pid = msg.get("pid")
            if pid is not None:
                return {"type": "kill_result", **self.kill_process(int(pid))}
            return {"type": "kill_result", "success": False, "error": "No PID provided"}
        elif cmd == "ping":
            return {"type": "pong", "timestamp": datetime.now().isoformat()}
        return {"type": "error", "message": f"Unknown command: {cmd}"}


# ─────────────────────────────────────────────
# Server Connection (controller side)
# ─────────────────────────────────────────────

class ServerConnection:
    """Manages a connection to a single remote agent."""

    HISTORY_SIZE = 300

    def __init__(self, config: ServerConfig):
        self.config = config
        self.status = ServerStatus.OFFLINE
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._metrics_history: deque = deque(maxlen=self.HISTORY_SIZE)
        self._latest_metrics: Optional[SystemMetrics] = None
        self._latest_screen: Optional[str] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._running = False
        self._poll_interval = 5  # seconds

    # ── connection management ───────────────

    def connect(self) -> bool:
        with self._lock:
            if self._sock:
                return True
            self.status = ServerStatus.CONNECTING
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.config.host, self.config.port))
            sock.settimeout(None)
            with self._lock:
                self._sock = sock
                self.status = ServerStatus.ONLINE
            return True
        except Exception as e:
            with self._lock:
                self.status = ServerStatus.OFFLINE
            return False

    def disconnect(self) -> None:
        self._running = False
        with self._lock:
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self.status = ServerStatus.OFFLINE

    def start_polling(self) -> None:
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop_polling(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        while self._running:
            if self.status != ServerStatus.ONLINE:
                self.connect()
            if self.status == ServerStatus.ONLINE:
                self._fetch_metrics()
            time.sleep(self._poll_interval)

    def _send_command(self, command: Dict) -> Optional[Dict]:
        with self._lock:
            sock = self._sock
        if sock is None:
            return None
        try:
            send_message(sock, command)
            return recv_message(sock)
        except Exception:
            with self._lock:
                self._sock = None
                self.status = ServerStatus.OFFLINE
            return None

    def _fetch_metrics(self) -> None:
        response = self._send_command({"command": "get_metrics"})
        if response and response.get("type") == "metrics":
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
                for p in response.get("processes", [])
            ]
            metrics = SystemMetrics(
                timestamp=datetime.fromisoformat(response["timestamp"]),
                cpu_percent=response["cpu_percent"],
                ram_percent=response["ram_percent"],
                ram_used_mb=response["ram_used_mb"],
                ram_total_mb=response["ram_total_mb"],
                net_bytes_sent=response["net_bytes_sent"],
                net_bytes_recv=response["net_bytes_recv"],
                processes=procs,
            )
            self._latest_metrics = metrics
            self._metrics_history.append(metrics)

    # ── public API ──────────────────────────

    def get_metrics(self) -> Optional[SystemMetrics]:
        return self._latest_metrics

    def get_metrics_history(self) -> List[SystemMetrics]:
        return list(self._metrics_history)

    def get_screen(self) -> Optional[str]:
        response = self._send_command({"command": "get_screen"})
        if response and response.get("type") == "screen":
            self._latest_screen = response.get("data")
            return self._latest_screen
        return None

    def kill_process(self, pid: int) -> Dict:
        response = self._send_command({"command": "kill_process", "pid": pid})
        if response:
            return response
        return {"success": False, "error": "No response from agent"}

    def ping(self) -> bool:
        response = self._send_command({"command": "ping"})
        return response is not None and response.get("type") == "pong"


# ─────────────────────────────────────────────
# Task Manager
# ─────────────────────────────────────────────

class TaskManager:
    """Manages tasks with persistence."""

    def __init__(self, storage_path: str = "nexus_tasks.json"):
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
        task_id = f"task_{int(time.time() * 1000)}_{len(self._tasks)}"
        now = datetime.now()
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

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.now()
            if task.status == TaskStatus.COMPLETED and task.completed_at is None:
                task.completed_at = datetime.now()
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
# Server Manager (controller)
# ─────────────────────────────────────────────

class ServerManager:
    """Manages multiple server connections."""

    def __init__(self, storage_path: str = "nexus_servers.json"):
        self.storage_path = storage_path
        self._servers: Dict[str, ServerConfig] = {}
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
                    self._servers[cfg.server_id] = cfg
            except Exception:
                pass

    def _save(self) -> None:
        try:
            with open(self.storage_path, "w") as f:
                json.dump([s.to_dict() for s in self._servers.values()], f, indent=2)
        except Exception:
            pass

    def add_server(self, name: str, host: str, port: int, description: str = "") -> ServerConfig:
        server_id = f"srv_{int(time.time() * 1000)}"
        cfg = ServerConfig(server_id=server_id, name=name, host=host, port=port, description=description)
        with self._lock:
            self._servers[server_id] = cfg
            self._save()
        return cfg

    def remove_server(self, server_id: str) -> bool:
        with self._lock:
            if server_id in self._connections:
                self._connections[server_id].disconnect()
                del self._connections[server_id]
            if server_id in self._servers:
                del self._servers[server_id]
                self._save()
                return True
            return False

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        return self._servers.get(server_id)

    def get_all_servers(self) -> List[ServerConfig]:
        return list(self._servers.values())

    def get_connection(self, server_id: str) -> Optional[ServerConnection]:
        return self._connections.get(server_id)

    def connect_server(self, server_id: str) -> bool:
        cfg = self._servers.get(server_id)
        if cfg is None:
            return False
        with self._lock:
            if server_id not in self._connections:
                conn = ServerConnection(cfg)
                self._connections[server_id] = conn
        conn = self._connections[server_id]
        success = conn.connect()
        if success:
            conn.start_polling()
        return success

    def disconnect_server(self, server_id: str) -> None:
        conn = self._connections.get(server_id)
        if conn:
            conn.disconnect()

    def disconnect_all(self) -> None:
        for conn in self._connections.values():
            conn.disconnect()

    def get_server_status(self, server_id: str) -> ServerStatus:
        conn = self._connections.get(server_id)
        if conn is None:
            return ServerStatus.OFFLINE
        return conn.status


# ─────────────────────────────────────────────
# NexusCtrl Core
# ─────────────────────────────────────────────

class NexusCtrl:
    """Main controller tying everything together."""

    def __init__(self):
        self.server_manager = ServerManager()
        self.task_manager = TaskManager()

    def shutdown(self) -> None:
        self.server_manager.disconnect_all()

    # ── convenience wrappers ────────────────

    def add_server(self, name: str, host: str, port: int, description: str = "") -> ServerConfig:
        return self.server_manager.add_server(name, host, port, description)

    def remove_server(self, server_id: str) -> bool:
        return self.server_manager.remove_server(server_id)

    def connect(self, server_id: str) -> bool:
        return self.server_manager.connect_server(server_id)

    def disconnect(self, server_id: str) -> None:
        self.server_manager.disconnect_server(server_id)

    def get_metrics(self, server_id: str) -> Optional[SystemMetrics]:
        conn = self.server_manager.get_connection(server_id)
        return conn.get_metrics() if conn else None

    def get_metrics_history(self, server_id: str) -> List[SystemMetrics]:
        conn = self.server_manager.get_connection(server_id)
        return conn.get_metrics_history() if conn else []

    def get_screen(self, server_id: str) -> Optional[str]:
        conn = self.server_manager.get_connection(server_id)
        return conn.get_screen() if conn else None

    def kill_process(self, server_id: str, pid: int) -> Dict:
        conn = self.server_manager.get_connection(server_id)
        if conn:
            return conn.kill_process(pid)
        return {"success": False, "error": "Not connected"}

    def create_task(self, title: str, description: str, priority: TaskPriority, server_id: Optional[str] = None) -> Task:
        return self.task_manager.create_task(title, description, priority, server_id)

    def complete_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.update_task(task_id, status=TaskStatus.COMPLETED)

    def cancel_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.update_task(task_id, status=TaskStatus.CANCELLED)


# ─────────────────────────────────────────────
# GUI (Tkinter)
# ─────────────────────────────────────────────

if HAS_TK:

    class NexusGUI:
        """Main GUI application."""

        PRIORITY_COLORS = {
            TaskPriority.CRITICAL: "#ff4444",
            TaskPriority.HIGH: "#ff8800",
            TaskPriority.MEDIUM: "#ffcc00",
            TaskPriority.LOW: "#44bb44",
        }

        def __init__(self, ctrl: NexusCtrl):
            self.ctrl = ctrl
            self.root = tk.Tk()
            self.root.title("NexusCtrl - RDP Server Management")
            self.root.geometry("1200x750")
            self.root.configure(bg="#1e1e2e")
            self._selected_server_id: Optional[str] = None
            self._build_ui()
            self._start_refresh()

        # ── UI construction ─────────────────

        def _build_ui(self) -> None:
            self._build_menu()
            main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1e1e2e", sashwidth=4)
            main.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            left = self._build_left_panel(main)
            right = self._build_right_panel(main)
            main.add(left, minsize=220)
            main.add(right, minsize=700)

        def _build_menu(self) -> None:
            menubar = tk.Menu(self.root)
            srv_menu = tk.Menu(menubar, tearoff=0)
            srv_menu.add_command(label="Add Server", command=self._dialog_add_server)
            srv_menu.add_command(label="Remove Server", command=self._remove_selected_server)
            srv_menu.add_separator()
            srv_menu.add_command(label="Exit", command=self._on_close)
            menubar.add_cascade(label="Servers", menu=srv_menu)

            task_menu = tk.Menu(menubar, tearoff=0)
            task_menu.add_command(label="New Task", command=self._dialog_add_task)
            menubar.add_cascade(label="Tasks", menu=task_menu)

            agent_menu = tk.Menu(menubar, tearoff=0)
            agent_menu.add_command(label="Start Agent Here", command=self._start_local_agent)
            menubar.add_cascade(label="Agent", menu=agent_menu)

            self.root.config(menu=menubar)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        def _build_left_panel(self, parent) -> tk.Frame:
            frame = tk.Frame(parent, bg="#181825", width=220)
            tk.Label(frame, text="SERVERS", bg="#181825", fg="#cdd6f4",
                     font=("Consolas", 10, "bold")).pack(pady=(8, 2))
            self._server_listbox = tk.Listbox(
                frame, bg="#1e1e2e", fg="#cdd6f4", selectbackground="#313244",
                font=("Consolas", 10), borderwidth=0, highlightthickness=0
            )
            self._server_listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self._server_listbox.bind("<<ListboxSelect>>", self._on_server_select)

            btn_frame = tk.Frame(frame, bg="#181825")
            btn_frame.pack(fill=tk.X, padx=4, pady=4)
            tk.Button(btn_frame, text="Connect", command=self._connect_selected,
                      bg="#313244", fg="#a6e3a1", font=("Consolas", 9),
                      relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            tk.Button(btn_frame, text="Disconnect", command=self._disconnect_selected,
                      bg="#313244", fg="#f38ba8", font=("Consolas", 9),
                      relief=tk.FLAT).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            return frame

        def _build_right_panel(self, parent) -> tk.Frame:
            frame = tk.Frame(parent, bg="#1e1e2e")
            self._notebook = ttk.Notebook(frame)
            self._notebook.pack(fill=tk.BOTH, expand=True)

            style = ttk.Style()
            style.theme_use("default")
            style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
            style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                            padding=[10, 4], font=("Consolas", 9))
            style.map("TNotebook.Tab", background=[("selected", "#45475a")])

            self._tab_overview = self._build_tab_overview()
            self._tab_processes = self._build_tab_processes()
            self._tab_screen = self._build_tab_screen()
            self._tab_tasks = self._build_tab_tasks()
            self._tab_history = self._build_tab_history()

            self._notebook.add(self._tab_overview, text="Overview")
            self._notebook.add(self._tab_processes, text="Processes")
            self._notebook.add(self._tab_screen, text="Screen")
            self._notebook.add(self._tab_tasks, text="Tasks")
            self._notebook.add(self._tab_history, text="History")
            return frame

        def _build_tab_overview(self) -> tk.Frame:
            frame = tk.Frame(self._notebook, bg="#1e1e2e")
            self._lbl_status = tk.Label(frame, text="Status: —", bg="#1e1e2e", fg="#cdd6f4",
                                        font=("Consolas", 11, "bold"))
            self._lbl_status.pack(anchor=tk.W, padx=12, pady=(12, 4))
            self._lbl_cpu = tk.Label(frame, text="CPU: —", bg="#1e1e2e", fg="#89b4fa",
                                     font=("Consolas", 10))
            self._lbl_cpu.pack(anchor=tk.W, padx=12)
            self._lbl_ram = tk.Label(frame, text="RAM: —", bg="#1e1e2e", fg="#cba6f7",
                                     font=("Consolas", 10))
            self._lbl_ram.pack(anchor=tk.W, padx=12)
            self._lbl_net = tk.Label(frame, text="Network: —", bg="#1e1e2e", fg="#94e2d5",
                                     font=("Consolas", 10))
            self._lbl_net.pack(anchor=tk.W, padx=12)
            self._lbl_ts = tk.Label(frame, text="Last update: —", bg="#1e1e2e", fg="#585b70",
                                    font=("Consolas", 9))
            self._lbl_ts.pack(anchor=tk.W, padx=12, pady=(4, 0))
            return frame

        def _build_tab_processes(self) -> tk.Frame:
            frame = tk.Frame(self._notebook, bg="#1e1e2e")
            cols = ("PID", "Name", "CPU%", "RAM MB", "Status", "User")
            self._proc_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                           selectmode="browse")
            for col in cols:
                self._proc_tree.heading(col, text=col)
                self._proc_tree.column(col, width=120, anchor=tk.W)
            self._proc_tree.column("PID", width=70)
            self._proc_tree.column("CPU%", width=70)
            self._proc_tree.column("RAM MB", width=80)

            style = ttk.Style()
            style.configure("Treeview", background="#1e1e2e", foreground="#cdd6f4",
                            fieldbackground="#1e1e2e", rowheight=22,
                            font=("Consolas", 9))
            style.configure("Treeview.Heading", background="#313244", foreground="#cdd6f4",
                            font=("Consolas", 9, "bold"))
            style.map("Treeview", background=[("selected", "#45475a")])

            vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._proc_tree.yview)
            self._proc_tree.configure(yscrollcommand=vsb.set)
            self._proc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)

            btn = tk.Button(frame, text="Kill Selected Process",
                            command=self._kill_selected_process,
                            bg="#f38ba8", fg="#1e1e2e", font=("Consolas", 9, "bold"),
                            relief=tk.FLAT)
            btn.pack(side=tk.BOTTOM, pady=6)
            return frame

        def _build_tab_screen(self) -> tk.Frame:
            frame = tk.Frame(self._notebook, bg="#1e1e2e")
            self._screen_label = tk.Label(frame, bg="#181825",
                                          text="No screen capture available",
                                          fg="#585b70", font=("Consolas", 10))
            self._screen_label.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            tk.Button(frame, text="Refresh Screen", command=self._refresh_screen,
                      bg="#313244", fg="#cdd6f4", font=("Consolas", 9),
                      relief=tk.FLAT).pack(pady=4)
            return frame

        def _build_tab_tasks(self) -> tk.Frame:
            frame = tk.Frame(self._notebook, bg="#1e1e2e")
            top = tk.Frame(frame, bg="#1e1e2e")
            top.pack(fill=tk.X, padx=8, pady=4)
            tk.Button(top, text="+ New Task", command=self._dialog_add_task,
                      bg="#a6e3a1", fg="#1e1e2e", font=("Consolas", 9, "bold"),
                      relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
            tk.Button(top, text="Complete", command=self._complete_task,
                      bg="#89b4fa", fg="#1e1e2e", font=("Consolas", 9),
                      relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
            tk.Button(top, text="Cancel", command=self._cancel_task,
                      bg="#f38ba8", fg="#1e1e2e", font=("Consolas", 9),
                      relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
            tk.Button(top, text="Delete", command=self._delete_task,
                      bg="#585b70", fg="#cdd6f4", font=("Consolas", 9),
                      relief=tk.FLAT).pack(side=tk.LEFT, padx=2)

            cols = ("Title", "Priority", "Status", "Server", "Created")
            self._task_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                           selectmode="browse")
            for col in cols:
                self._task_tree.heading(col, text=col)
                self._task_tree.column(col, width=150, anchor=tk.W)
            vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self._task_tree.yview)
            self._task_tree.configure(yscrollcommand=vsb.set)
            self._task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
            vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
            return frame

        def _build_tab_history(self) -> tk.Frame:
            frame = tk.Frame(self._notebook, bg="#1e1e2e")
            self._history_text = scrolledtext.ScrolledText(
                frame, bg="#181825", fg="#cdd6f4", font=("Consolas", 9),
                state=tk.DISABLED, borderwidth=0
            )
            self._history_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            return frame

        # ── refresh loop ────────────────────

        def _start_refresh(self) -> None:
            self._refresh_server_list()
            self._refresh_tasks()
            self._schedule_refresh()

        def _schedule_refresh(self) -> None:
            self.root.after(3000, self._periodic_refresh)

        def _periodic_refresh(self) -> None:
            self._refresh_server_list()
            self._refresh_overview()
            self._refresh_processes()
            self._refresh_tasks()
            self._refresh_history()
            self._schedule_refresh()

        def _refresh_server_list(self) -> None:
            servers = self.ctrl.server_manager.get_all_servers()
            self._server_listbox.delete(0, tk.END)
            self._server_ids: List[str] = []
            for srv in servers:
                status = self.ctrl.server_manager.get_server_status(srv.server_id)
                indicator = "●" if status == ServerStatus.ONLINE else "○"
                self._server_listbox.insert(tk.END, f"{indicator} {srv.name} ({srv.host}:{srv.port})")
                self._server_ids.append(srv.server_id)

        def _refresh_overview(self) -> None:
            if not self._selected_server_id:
                return
            status = self.ctrl.server_manager.get_server_status(self._selected_server_id)
            self._lbl_status.config(text=f"Status: {status.value.upper()}")
            metrics = self.ctrl.get_metrics(self._selected_server_id)
            if metrics:
                self._lbl_cpu.config(text=f"CPU: {metrics.cpu_percent:.1f}%")
                self._lbl_ram.config(
                    text=f"RAM: {metrics.ram_percent:.1f}% ({metrics.ram_used_mb:.0f} / {metrics.ram_total_mb:.0f} MB)"
                )
                sent_mb = metrics.net_bytes_sent / 1024 / 1024
                recv_mb = metrics.net_bytes_recv / 1024 / 1024
                self._lbl_net.config(text=f"Net ↑{sent_mb:.1f} MB  ↓{recv_mb:.1f} MB")
                self._lbl_ts.config(text=f"Last update: {metrics.timestamp.strftime('%H:%M:%S')}")

        def _refresh_processes(self) -> None:
            if not self._selected_server_id:
                return
            metrics = self.ctrl.get_metrics(self._selected_server_id)
            if not metrics:
                return
            for row in self._proc_tree.get_children():
                self._proc_tree.delete(row)
            procs = sorted(metrics.processes, key=lambda p: p.cpu_percent, reverse=True)
            for p in procs:
                self._proc_tree.insert("", tk.END, iid=str(p.pid),
                                       values=(p.pid, p.name, f"{p.cpu_percent:.1f}",
                                               f"{p.memory_mb:.1f}", p.status, p.username))

        def _refresh_tasks(self) -> None:
            for row in self._task_tree.get_children():
                self._task_tree.delete(row)
            tasks = sorted(self.ctrl.task_manager.get_all_tasks(),
                           key=lambda t: t.created_at, reverse=True)
            for task in tasks:
                srv_name = ""
                if task.server_id:
                    cfg = self.ctrl.server_manager.get_server(task.server_id)
                    srv_name = cfg.name if cfg else task.server_id
                self._task_tree.insert(
                    "", tk.END, iid=task.task_id,
                    values=(task.title, task.priority.value, task.status.value,
                            srv_name, task.created_at.strftime("%Y-%m-%d %H:%M"))
                )

        def _refresh_history(self) -> None:
            if not self._selected_server_id:
                return
            history = self.ctrl.get_metrics_history(self._selected_server_id)
            self._history_text.config(state=tk.NORMAL)
            self._history_text.delete("1.0", tk.END)
            for m in reversed(history[-50:]):
                line = (f"[{m.timestamp.strftime('%H:%M:%S')}] "
                        f"CPU={m.cpu_percent:.1f}%  "
                        f"RAM={m.ram_percent:.1f}%  "
                        f"Net↑{m.net_bytes_sent//1024}KB ↓{m.net_bytes_recv//1024}KB\n")
                self._history_text.insert(tk.END, line)
            self._history_text.config(state=tk.DISABLED)

        # ── event handlers ──────────────────

        def _on_server_select(self, event) -> None:
            sel = self._server_listbox.curselection()
            if sel:
                idx = sel[0]
                if idx < len(self._server_ids):
                    self._selected_server_id = self._server_ids[idx]
                    self._refresh_overview()
                    self._refresh_processes()
                    self._refresh_history()

        def _connect_selected(self) -> None:
            if not self._selected_server_id:
                messagebox.showwarning("NexusCtrl", "Select a server first.")
                return
            threading.Thread(
                target=self.ctrl.connect,
                args=(self._selected_server_id,),
                daemon=True
            ).start()

        def _disconnect_selected(self) -> None:
            if self._selected_server_id:
                self.ctrl.disconnect(self._selected_server_id)

        def _remove_selected_server(self) -> None:
            if not self._selected_server_id:
                messagebox.showwarning("NexusCtrl", "Select a server first.")
                return
            if messagebox.askyesno("Remove Server", "Remove selected server?"):
                self.ctrl.remove_server(self._selected_server_id)
                self._selected_server_id = None
                self._refresh_server_list()

        def _kill_selected_process(self) -> None:
            if not self._selected_server_id:
                messagebox.showwarning("NexusCtrl", "Select a server first.")
                return
            sel = self._proc_tree.selection()
            if not sel:
                messagebox.showwarning("NexusCtrl", "Select a process first.")
                return
            pid = int(sel[0])
            if messagebox.askyesno("Kill Process", f"Kill process PID {pid}?"):
                result = self.ctrl.kill_process(self._selected_server_id, pid)
                if result.get("success"):
                    messagebox.showinfo("NexusCtrl", f"Process {pid} terminated.")
                else:
                    messagebox.showerror("NexusCtrl", f"Failed: {result.get('error')}")

        def _refresh_screen(self) -> None:
            if not self._selected_server_id:
                messagebox.showwarning("NexusCtrl", "Select a server first.")
                return

            def _fetch():
                data = self.ctrl.get_screen(self._selected_server_id)
                if data and Image:
                    try:
                        img_bytes = base64.b64decode(data)
                        img = Image.open(io.BytesIO(img_bytes))
                        # Fit to label
                        w = self._screen_label.winfo_width() or 800
                        h = self._screen_label.winfo_height() or 500
                        img.thumbnail((w, h), Image.LANCZOS)
                        from PIL import ImageTk
                        photo = ImageTk.PhotoImage(img)
                        self.root.after(0, lambda: self._update_screen_label(photo))
                    except Exception as e:
                        self.root.after(0, lambda: self._screen_label.config(
                            text=f"Error: {e}", image=""))
                else:
                    self.root.after(0, lambda: self._screen_label.config(
                        text="No screen data", image=""))

            threading.Thread(target=_fetch, daemon=True).start()

        def _update_screen_label(self, photo) -> None:
            self._screen_label.config(image=photo, text="")
            self._screen_label._photo = photo  # prevent GC

        def _complete_task(self) -> None:
            sel = self._task_tree.selection()
            if sel:
                self.ctrl.complete_task(sel[0])
                self._refresh_tasks()

        def _cancel_task(self) -> None:
            sel = self._task_tree.selection()
            if sel:
                self.ctrl.cancel_task(sel[0])
                self._refresh_tasks()

        def _delete_task(self) -> None:
            sel = self._task_tree.selection()
            if sel:
                if messagebox.askyesno("Delete Task", "Delete selected task?"):
                    self.ctrl.task_manager.delete_task(sel[0])
                    self._refresh_tasks()

        # ── dialogs ─────────────────────────

        def _dialog_add_server(self) -> None:
            dlg = tk.Toplevel(self.root)
            dlg.title("Add Server")
            dlg.configure(bg="#1e1e2e")
            dlg.resizable(False, False)
            fields = {}
            for label, default in [("Name", "My Server"), ("Host", "127.0.0.1"),
                                    ("Port", "9000"), ("Description", "")]:
                row = tk.Frame(dlg, bg="#1e1e2e")
                row.pack(fill=tk.X, padx=12, pady=4)
                tk.Label(row, text=label, bg="#1e1e2e", fg="#cdd6f4",
                         font=("Consolas", 9), width=12, anchor=tk.W).pack(side=tk.LEFT)
                var = tk.StringVar(value=default)
                tk.Entry(row, textvariable=var, bg="#313244", fg="#cdd6f4",
                         font=("Consolas", 9), insertbackground="#cdd6f4",
                         relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True)
                fields[label] = var

            def _submit():
                try:
                    self.ctrl.add_server(
                        name=fields["Name"].get(),
                        host=fields["Host"].get(),
                        port=int(fields["Port"].get()),
                        description=fields["Description"].get(),
                    )
                    self._refresh_server_list()
                    dlg.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            tk.Button(dlg, text="Add", command=_submit,
                      bg="#a6e3a1", fg="#1e1e2e", font=("Consolas", 9, "bold"),
                      relief=tk.FLAT).pack(pady=8)

        def _dialog_add_task(self) -> None:
            dlg = tk.Toplevel(self.root)
            dlg.title("New Task")
            dlg.configure(bg="#1e1e2e")
            dlg.resizable(False, False)

            fields = {}
            for label, default in [("Title", "New Task"), ("Description", "")]:
                row = tk.Frame(dlg, bg="#1e1e2e")
                row.pack(fill=tk.X, padx=12, pady=4)
                tk.Label(row, text=label, bg="#1e1e2e", fg="#cdd6f4",
                         font=("Consolas", 9), width=12, anchor=tk.W).pack(side=tk.LEFT)
                var = tk.StringVar(value=default)
                tk.Entry(row, textvariable=var, bg="#313244", fg="#cdd6f4",
                         font=("Consolas", 9), insertbackground="#cdd6f4",
                         relief=tk.FLAT, width=30).pack(side=tk.LEFT)
                fields[label] = var

            # Priority
            prow = tk.Frame(dlg, bg="#1e1e2e")
            prow.pack(fill=tk.X, padx=12, pady=4)
            tk.Label(prow, text="Priority", bg="#1e1e2e", fg="#cdd6f4",
                     font=("Consolas", 9), width=12, anchor=tk.W).pack(side=tk.LEFT)
            priority_var = tk.StringVar(value=TaskPriority.MEDIUM.value)
            ttk.Combobox(prow, textvariable=priority_var,
                         values=[p.value for p in TaskPriority],
                         state="readonly", width=15).pack(side=tk.LEFT)

            # Server
            srow = tk.Frame(dlg, bg="#1e1e2e")
            srow.pack(fill=tk.X, padx=12, pady=4)
            tk.Label(srow, text="Server", bg="#1e1e2e", fg="#cdd6f4",
                     font=("Consolas", 9), width=12, anchor=tk.W).pack(side=tk.LEFT)
            servers = self.ctrl.server_manager.get_all_servers()
            srv_options = ["(none)"] + [f"{s.name} ({s.server_id})" for s in servers]
            srv_var = tk.StringVar(value="(none)")
            ttk.Combobox(srow, textvariable=srv_var, values=srv_options,
                         state="readonly", width=25).pack(side=tk.LEFT)

            def _submit():
                srv_id = None
                if srv_var.get() != "(none)":
                    # extract server_id from selection
                    for s in servers:
                        if f"{s.name} ({s.server_id})" == srv_var.get():
                            srv_id = s.server_id
                            break
                self.ctrl.create_task(
                    title=fields["Title"].get(),
                    description=fields["Description"].get(),
                    priority=TaskPriority(priority_var.get()),
                    server_id=srv_id,
                )
                self._refresh_tasks()
                dlg.destroy()

            tk.Button(dlg, text="Create", command=_submit,
                      bg="#a6e3a1", fg="#1e1e2e", font=("Consolas", 9, "bold"),
                      relief=tk.FLAT).pack(pady=8)

        def _start_local_agent(self) -> None:
            port_dlg = tk.Toplevel(self.root)
            port_dlg.title("Start Agent")
            port_dlg.configure(bg="#1e1e2e")
            port_dlg.resizable(False, False)
            row = tk.Frame(port_dlg, bg="#1e1e2e")
            row.pack(padx=12, pady=8)
            tk.Label(row, text="Port:", bg="#1e1e2e", fg="#cdd6f4",
                     font=("Consolas", 9)).pack(side=tk.LEFT)
            port_var = tk.StringVar(value="9000")
            tk.Entry(row, textvariable=port_var, bg="#313244", fg="#cdd6f4",
                     font=("Consolas", 9), insertbackground="#cdd6f4",
                     relief=tk.FLAT, width=8).pack(side=tk.LEFT, padx=4)

            def _start():
                try:
                    port = int(port_var.get())
                    agent = NexusAgent(host="0.0.0.0", port=port)
                    agent.start()
                    messagebox.showinfo("Agent", f"Agent started on port {port}")
                    port_dlg.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            tk.Button(port_dlg, text="Start", command=_start,
                      bg="#a6e3a1", fg="#1e1e2e", font=("Consolas", 9, "bold"),
                      relief=tk.FLAT).pack(pady=4)

        def _on_close(self) -> None:
            self.ctrl.shutdown()
            self.root.destroy()

        def run(self) -> None:
            self.root.mainloop()


# ─────────────────────────────────────────────
# CLI fallback
# ─────────────────────────────────────────────

class NexusCLI:
    """Simple CLI interface when Tkinter is unavailable."""

    def __init__(self, ctrl: NexusCtrl):
        self.ctrl = ctrl

    def run(self) -> None:
        print("NexusCtrl CLI")
        print("Commands: add, remove, connect, disconnect, metrics, processes, kill, tasks, newtask, quit")
        while True:
            try:
                cmd = input("\nnexus> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if cmd == "quit":
                break
            elif cmd == "add":
                name = input("Name: ")
                host = input("Host: ")
                port = int(input("Port [9000]: ") or "9000")
                desc = input("Description: ")
                srv = self.ctrl.add_server(name, host, port, desc)
                print(f"Added server {srv.server_id}")
            elif cmd == "remove":
                sid = input("Server ID: ")
                print("Removed" if self.ctrl.remove_server(sid) else "Not found")
            elif cmd == "connect":
                sid = input("Server ID: ")
                print("Connected" if self.ctrl.connect(sid) else "Failed")
            elif cmd == "disconnect":
                sid = input("Server ID: ")
                self.ctrl.disconnect(sid)
                print("Disconnected")
            elif cmd == "metrics":
                sid = input("Server ID: ")
                m = self.ctrl.get_metrics(sid)
                if m:
                    print(f"CPU: {m.cpu_percent:.1f}%  RAM: {m.ram_percent:.1f}%  "
                          f"Net↑{m.net_bytes_sent//1024}KB ↓{m.net_bytes_recv//1024}KB")
                else:
                    print("No metrics available")
            elif cmd == "processes":
                sid = input("Server ID: ")
                m = self.ctrl.get_metrics(sid)
                if m:
                    for p in sorted(m.processes, key=lambda x: x.cpu_percent, reverse=True)[:20]:
                        print(f"  {p.pid:6d}  {p.name[:25]:25s}  CPU:{p.cpu_percent:5.1f}%  RAM:{p.memory_mb:7.1f}MB")
                else:
                    print("No data")
            elif cmd == "kill":
                sid = input("Server ID: ")
                pid = int(input("PID: "))
                result = self.ctrl.kill_process(sid, pid)
                print(result)
            elif cmd == "tasks":
                for t in self.ctrl.task_manager.get_all_tasks():
                    print(f"  [{t.task_id}] {t.title} | {t.priority.value} | {t.status.value}")
            elif cmd == "newtask":
                title = input("Title: ")
                desc = input("Description: ")
                pri = input("Priority (critical/high/medium/low) [medium]: ") or "medium"
                sid = input("Server ID (blank for none): ") or None
                task = self.ctrl.create_task(title, desc, TaskPriority(pri), sid)
                print(f"Created task {task.task_id}")
            elif cmd == "servers":
                for s in self.ctrl.server_manager.get_all_servers():
                    status = self.ctrl.server_manager.get_server_status(s.server_id)
                    print(f"  [{s.server_id}] {s.name} {s.host}:{s.port} — {status.value}")
            elif cmd == "agent":
                port = int(input("Port [9000]: ") or "9000")
                agent = NexusAgent(host="0.0.0.0", port=port)
                agent.start()
                print(f"Agent running on port {port}. Press Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    agent.stop()
            else:
                print("Unknown command. Try: add, remove, connect, disconnect, metrics, processes, kill, tasks, newtask, servers, agent, quit")
        self.ctrl.shutdown()
        print("Goodbye.")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    ctrl = NexusCtrl()

    if "--agent" in sys.argv:
        port = 9000
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        agent = NexusAgent(host="0.0.0.0", port=port)
        agent.start()
        print(f"NexusCtrl Agent running on port {port}. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            agent.stop()
            print("Agent stopped.")
        return

    if "--cli" in sys.argv or not HAS_TK:
        cli = NexusCLI(ctrl)
        cli.run()
    else:
        gui = NexusGUI(ctrl)
        gui.run()


if __name__ == "__main__":
    main()