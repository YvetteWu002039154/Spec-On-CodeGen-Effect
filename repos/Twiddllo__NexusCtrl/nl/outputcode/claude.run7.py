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
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import psutil

try:
    import PIL.ImageGrab as ImageGrab
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


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
class Task:
    task_id: str
    title: str
    description: str
    priority: TaskPriority
    completed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    server_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "server_id": self.server_id
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        data = data.copy()
        data['priority'] = TaskPriority(data['priority'])
        return cls(**data)


@dataclass
class ServerMetrics:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    net_bytes_sent: int = 0
    net_bytes_recv: int = 0
    net_sent_speed: float = 0.0
    net_recv_speed: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_gb": self.ram_used_gb,
            "ram_total_gb": self.ram_total_gb,
            "net_bytes_sent": self.net_bytes_sent,
            "net_bytes_recv": self.net_bytes_recv,
            "net_sent_speed": self.net_sent_speed,
            "net_recv_speed": self.net_recv_speed,
            "timestamp": self.timestamp
        }


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    username: str = ""

    def to_dict(self) -> Dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "status": self.status,
            "username": self.username
        }


@dataclass
class Server:
    server_id: str
    name: str
    host: str
    port: int
    status: ServerStatus = ServerStatus.OFFLINE
    metrics: Optional[ServerMetrics] = None
    processes: List[ProcessInfo] = field(default_factory=list)
    metrics_history: List[ServerMetrics] = field(default_factory=list)
    last_seen: Optional[str] = None
    screen_data: Optional[bytes] = None
    max_history: int = 60

    def update_metrics(self, metrics: ServerMetrics):
        self.metrics = metrics
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
        self.last_seen = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "host": self.host,
            "port": self.port
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Server':
        return cls(**data)


class AgentProtocol:
    HEADER_SIZE = 8
    MSG_METRICS = 0x01
    MSG_PROCESSES = 0x02
    MSG_SCREEN = 0x03
    MSG_KILL_PROCESS = 0x04
    MSG_KILL_ACK = 0x05
    MSG_PING = 0x06
    MSG_PONG = 0x07
    MSG_ERROR = 0xFF

    @staticmethod
    def pack_message(msg_type: int, data: bytes) -> bytes:
        length = len(data)
        header = struct.pack('>II', msg_type, length)
        return header + data

    @staticmethod
    def unpack_header(header: bytes) -> tuple:
        return struct.unpack('>II', header)

    @staticmethod
    def recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except Exception:
                return None
        return data

    @staticmethod
    def recv_message(sock: socket.socket) -> Optional[tuple]:
        header = AgentProtocol.recv_exact(sock, AgentProtocol.HEADER_SIZE)
        if not header:
            return None
        msg_type, length = AgentProtocol.unpack_header(header)
        if length > 0:
            data = AgentProtocol.recv_exact(sock, length)
            if data is None:
                return None
        else:
            data = b''
        return msg_type, data

    @staticmethod
    def send_message(sock: socket.socket, msg_type: int, data: bytes) -> bool:
        try:
            msg = AgentProtocol.pack_message(msg_type, data)
            sock.sendall(msg)
            return True
        except Exception:
            return False


class AgentServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 9999):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._prev_net = psutil.net_io_counters()
        self._prev_net_time = time.time()

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[Agent] Server started on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

    def _run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    print(f"[Agent] Connection from {addr}")
                    t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[Agent] Accept error: {e}")
        except Exception as e:
            print(f"[Agent] Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def _collect_metrics(self) -> ServerMetrics:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        net = psutil.net_io_counters()
        now = time.time()
        elapsed = now - self._prev_net_time
        if elapsed > 0:
            sent_speed = (net.bytes_sent - self._prev_net.bytes_sent) / elapsed
            recv_speed = (net.bytes_recv - self._prev_net.bytes_recv) / elapsed
        else:
            sent_speed = 0.0
            recv_speed = 0.0
        self._prev_net = net
        self._prev_net_time = now
        return ServerMetrics(
            cpu_percent=cpu,
            ram_percent=ram.percent,
            ram_used_gb=ram.used / (1024 ** 3),
            ram_total_gb=ram.total / (1024 ** 3),
            net_bytes_sent=net.bytes_sent,
            net_bytes_recv=net.bytes_recv,
            net_sent_speed=sent_speed,
            net_recv_speed=recv_speed
        )

    def _collect_processes(self) -> List[ProcessInfo]:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']):
            try:
                info = proc.info
                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=info['name'] or '',
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_percent=info['memory_percent'] or 0.0,
                    status=info['status'] or '',
                    username=info['username'] or ''
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return sorted(processes, key=lambda p: p.cpu_percent, reverse=True)[:50]

    def _capture_screen(self) -> Optional[bytes]:
        if not PIL_AVAILABLE:
            return None
        try:
            img = ImageGrab.grab()
            img = img.resize((800, 600), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=50)
            return buf.getvalue()
        except Exception as e:
            print(f"[Agent] Screen capture error: {e}")
            return None

    def _handle_client(self, conn: socket.socket, addr):
        conn.settimeout(30.0)
        try:
            while True:
                result = AgentProtocol.recv_message(conn)
                if result is None:
                    break
                msg_type, data = result

                if msg_type == AgentProtocol.MSG_PING:
                    AgentProtocol.send_message(conn, AgentProtocol.MSG_PONG, b'')

                elif msg_type == AgentProtocol.MSG_METRICS:
                    metrics = self._collect_metrics()
                    payload = json.dumps(metrics.to_dict()).encode()
                    AgentProtocol.send_message(conn, AgentProtocol.MSG_METRICS, payload)

                elif msg_type == AgentProtocol.MSG_PROCESSES:
                    procs = self._collect_processes()
                    payload = json.dumps([p.to_dict() for p in procs]).encode()
                    AgentProtocol.send_message(conn, AgentProtocol.MSG_PROCESSES, payload)

                elif msg_type == AgentProtocol.MSG_SCREEN:
                    screen = self._capture_screen()
                    if screen:
                        AgentProtocol.send_message(conn, AgentProtocol.MSG_SCREEN, screen)
                    else:
                        AgentProtocol.send_message(conn, AgentProtocol.MSG_ERROR, b'Screen capture unavailable')

                elif msg_type == AgentProtocol.MSG_KILL_PROCESS:
                    try:
                        pid = int(data.decode())
                        proc = psutil.Process(pid)
                        proc.terminate()
                        AgentProtocol.send_message(conn, AgentProtocol.MSG_KILL_ACK, f"Killed {pid}".encode())
                    except Exception as e:
                        AgentProtocol.send_message(conn, AgentProtocol.MSG_ERROR, str(e).encode())
                else:
                    AgentProtocol.send_message(conn, AgentProtocol.MSG_ERROR, b'Unknown command')
        except Exception as e:
            print(f"[Agent] Client error {addr}: {e}")
        finally:
            conn.close()
            print(f"[Agent] Disconnected {addr}")


class ServerConnection:
    def __init__(self, server: Server):
        self.server = server
        self.socket: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.server.host, self.server.port))
            self.socket = sock
            return True
        except Exception as e:
            print(f"[Client] Connect error to {self.server.host}:{self.server.port}: {e}")
            self.socket = None
            return False

    def disconnect(self):
        with self._lock:
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None

    def is_connected(self) -> bool:
        return self.socket is not None

    def ping(self) -> bool:
        with self._lock:
            if not self.socket:
                return False
            try:
                return AgentProtocol.send_message(self.socket, AgentProtocol.MSG_PING, b'')
            except Exception:
                return False

    def get_metrics(self) -> Optional[ServerMetrics]:
        with self._lock:
            if not self.socket:
                return None
            try:
                if not AgentProtocol.send_message(self.socket, AgentProtocol.MSG_METRICS, b''):
                    return None
                result = AgentProtocol.recv_message(self.socket)
                if result and result[0] == AgentProtocol.MSG_METRICS:
                    data = json.loads(result[1].decode())
                    return ServerMetrics(**data)
            except Exception as e:
                print(f"[Client] get_metrics error: {e}")
            return None

    def get_processes(self) -> Optional[List[ProcessInfo]]:
        with self._lock:
            if not self.socket:
                return None
            try:
                if not AgentProtocol.send_message(self.socket, AgentProtocol.MSG_PROCESSES, b''):
                    return None
                result = AgentProtocol.recv_message(self.socket)
                if result and result[0] == AgentProtocol.MSG_PROCESSES:
                    data = json.loads(result[1].decode())
                    return [ProcessInfo(**p) for p in data]
            except Exception as e:
                print(f"[Client] get_processes error: {e}")
            return None

    def get_screen(self) -> Optional[bytes]:
        with self._lock:
            if not self.socket:
                return None
            try:
                if not AgentProtocol.send_message(self.socket, AgentProtocol.MSG_SCREEN, b''):
                    return None
                result = AgentProtocol.recv_message(self.socket)
                if result and result[0] == AgentProtocol.MSG_SCREEN:
                    return result[1]
            except Exception as e:
                print(f"[Client] get_screen error: {e}")
            return None

    def kill_process(self, pid: int) -> bool:
        with self._lock:
            if not self.socket:
                return False
            try:
                if not AgentProtocol.send_message(self.socket, AgentProtocol.MSG_KILL_PROCESS, str(pid).encode()):
                    return False
                result = AgentProtocol.recv_message(self.socket)
                if result and result[0] == AgentProtocol.MSG_KILL_ACK:
                    return True
            except Exception as e:
                print(f"[Client] kill_process error: {e}")
            return False


class DataStore:
    def __init__(self, filepath: str = "nexusctrl_data.json"):
        self.filepath = filepath
        self._data: Dict = {
            "servers": [],
            "tasks": []
        }
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[DataStore] Load error: {e}")

    def save(self):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"[DataStore] Save error: {e}")

    def get_servers(self) -> List[Dict]:
        return self._data.get("servers", [])

    def save_server(self, server: Server):
        servers = self._data.get("servers", [])
        for i, s in enumerate(servers):
            if s["server_id"] == server.server_id:
                servers[i] = server.to_dict()
                self._data["servers"] = servers
                self.save()
                return
        servers.append(server.to_dict())
        self._data["servers"] = servers
        self.save()

    def delete_server(self, server_id: str):
        servers = self._data.get("servers", [])
        self._data["servers"] = [s for s in servers if s["server_id"] != server_id]
        self.save()

    def get_tasks(self) -> List[Dict]:
        return self._data.get("tasks", [])

    def save_task(self, task: Task):
        tasks = self._data.get("tasks", [])
        for i, t in enumerate(tasks):
            if t["task_id"] == task.task_id:
                tasks[i] = task.to_dict()
                self._data["tasks"] = tasks
                self.save()
                return
        tasks.append(task.to_dict())
        self._data["tasks"] = tasks
        self.save()

    def delete_task(self, task_id: str):
        tasks = self._data.get("tasks", [])
        self._data["tasks"] = [t for t in tasks if t["task_id"] != task_id]
        self.save()


class MonitoringManager:
    def __init__(self):
        self.servers: Dict[str, Server] = {}
        self.connections: Dict[str, ServerConnection] = {}
        self._monitor_threads: Dict[str, threading.Thread] = {}
        self._running: Dict[str, bool] = {}
        self._callbacks: List = []
        self._lock = threading.Lock()

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def _notify(self, event: str, data: Any = None):
        for cb in self._callbacks:
            try:
                cb(event, data)
            except Exception:
                pass

    def add_server(self, server: Server):
        with self._lock:
            self.servers[server.server_id] = server
            self.connections[server.server_id] = ServerConnection(server)

    def remove_server(self, server_id: str):
        self.stop_monitoring(server_id)
        with self._lock:
            self.servers.pop(server_id, None)
            conn = self.connections.pop(server_id, None)
            if conn:
                conn.disconnect()

    def start_monitoring(self, server_id: str, interval: float = 3.0):
        if server_id in self._running and self._running[server_id]:
            return
        self._running[server_id] = True
        t = threading.Thread(target=self._monitor_loop, args=(server_id, interval), daemon=True)
        self._monitor_threads[server_id] = t
        t.start()

    def stop_monitoring(self, server_id: str):
        self._running[server_id] = False
        conn = self.connections.get(server_id)
        if conn:
            conn.disconnect()

    def _monitor_loop(self, server_id: str, interval: float):
        server = self.servers.get(server_id)
        conn = self.connections.get(server_id)
        if not server or not conn:
            return

        while self._running.get(server_id, False):
            if not conn.is_connected():
                server.status = ServerStatus.CONNECTING
                self._notify("status_changed", server)
                if conn.connect():
                    server.status = ServerStatus.ONLINE
                    self._notify("status_changed", server)
                else:
                    server.status = ServerStatus.OFFLINE
                    self._notify("status_changed", server)
                    time.sleep(interval)
                    continue

            metrics = conn.get_metrics()
            if metrics:
                server.update_metrics(metrics)
                self._notify("metrics_updated", server)
            else:
                server.status = ServerStatus.OFFLINE
                conn.disconnect()
                self._notify("status_changed", server)

            time.sleep(interval)

    def get_processes(self, server_id: str) -> Optional[List[ProcessInfo]]:
        conn = self.connections.get(server_id)
        if conn and conn.is_connected():
            return conn.get_processes()
        return None

    def get_screen(self, server_id: str) -> Optional[bytes]:
        conn = self.connections.get(server_id)
        if conn and conn.is_connected():
            return conn.get_screen()
        return None

    def kill_process(self, server_id: str, pid: int) -> bool:
        conn = self.connections.get(server_id)
        if conn and conn.is_connected():
            return conn.kill_process(pid)
        return False


class TaskManager:
    def __init__(self, datastore: DataStore):
        self.datastore = datastore
        self.tasks: Dict[str, Task] = {}
        self._load_tasks()

    def _load_tasks(self):
        for t_dict in self.datastore.get_tasks():
            try:
                task = Task.from_dict(t_dict)
                self.tasks[task.task_id] = task
            except Exception as e:
                print(f"[TaskManager] Load task error: {e}")

    def create_task(self, title: str, description: str, priority: TaskPriority,
                    server_id: Optional[str] = None) -> Task:
        task_id = f"task_{int(time.time() * 1000)}"
        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            server_id=server_id
        )
        self.tasks[task_id] = task
        self.datastore.save_task(task)
        return task

    def complete_task(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if task:
            task.completed = True
            task.completed_at = datetime.now().isoformat()
            self.datastore.save_task(task)
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.datastore.delete_task(task_id)
            return True
        return False

    def get_tasks(self, completed: Optional[bool] = None,
                  priority: Optional[TaskPriority] = None) -> List[Task]:
        tasks = list(self.tasks.values())
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3
        }
        tasks.sort(key=lambda t: (t.completed, priority_order.get(t.priority, 99)))
        return tasks


class NexusCtrlApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NexusCtrl - RDP Server Management")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a2e')

        self.datastore = DataStore()
        self.monitoring = MonitoringManager()
        self.task_manager = TaskManager(self.datastore)

        self.monitoring.add_callback(self._on_monitoring_event)

        self._selected_server_id: Optional[str] = None
        self._screen_update_running = False
        self._screen_thread: Optional[threading.Thread] = None

        self._setup_styles()
        self._build_ui()
        self._load_servers()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        bg = '#1a1a2e'
        panel_bg = '#16213e'
        accent = '#0f3460'
        highlight = '#e94560'
        text_color = '#eaeaea'
        entry_bg = '#0f3460'

        style.configure('TFrame', background=bg)
        style.configure('Panel.TFrame', background=panel_bg)
        style.configure('TLabel', background=bg, foreground=text_color, font=('Consolas', 10))
        style.configure('Panel.TLabel', background=panel_bg, foreground=text_color, font=('Consolas', 10))
        style.configure('Title.TLabel', background=panel_bg, foreground=highlight,
                        font=('Consolas', 12, 'bold'))
        style.configure('Header.TLabel', background=bg, foreground=highlight,
                        font=('Consolas', 14, 'bold'))
        style.configure('TButton', background=accent, foreground=text_color,
                        font=('Consolas', 10), borderwidth=0, focusthickness=0)
        style.map('TButton', background=[('active', highlight)])
        style.configure('Danger.TButton', background='#8b0000', foreground=text_color,
                        font=('Consolas', 10))
        style.map('Danger.TButton', background=[('active', '#cc0000')])
        style.configure('Success.TButton', background='#006400', foreground=text_color,
                        font=('Consolas', 10))
        style.map('Success.TButton', background=[('active', '#008000')])
        style.configure('TNotebook', background=bg, borderwidth=0)
        style.configure('TNotebook.Tab', background=accent, foreground=text_color,
                        font=('Consolas', 10), padding=[10, 5])
        style.map('TNotebook.Tab', background=[('selected', highlight)])
        style.configure('Treeview', background=panel_bg, foreground=text_color,
                        fieldbackground=panel_bg, font=('Consolas', 9))
        style.configure('Treeview.Heading', background=accent, foreground=text_color,
                        font=('Consolas', 9, 'bold'))
        style.map('Treeview', background=[('selected', highlight)])
        style.configure('TEntry', fieldbackground=entry_bg, foreground=text_color,
                        insertcolor=text_color, font=('Consolas', 10))
        style.configure('TCombobox', fieldbackground=entry_bg, foreground=text_color,
                        background=accent, font=('Consolas', 10))
        style.configure('Horizontal.TProgressbar', background=highlight, troughcolor=accent)
        style.configure('TScrollbar', background=accent, troughcolor=panel_bg)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_panel = ttk.Frame(main_frame, style='Panel.TFrame', width=220)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)

        self._build_server_list(left_panel)

        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_processes = ttk.Frame(self.notebook)
        self.tab_screen = ttk.Frame(self.notebook)
        self.tab_tasks = ttk.Frame(self.notebook)
        self.tab_agent = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dashboard, text='Dashboard')
        self.notebook.add(self.tab_processes, text='Processes')
        self.notebook.add(self.tab_screen, text='Screen')
        self.notebook.add(self.tab_tasks, text='Tasks')
        self.notebook.add(self.tab_agent, text='Agent')

        self._build_dashboard_tab()
        self._build_processes_tab()
        self._build_screen_tab()
        self._build_tasks_tab()
        self._build_agent_tab()

        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

    def _build_server_list(self, parent):
        ttk.Label(parent, text="SERVERS", style='Title.TLabel').pack(pady=(10, 5), padx=10, anchor='w')

        btn_frame = ttk.Frame(parent, style='Panel.TFrame')
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Button(btn_frame, text="+ Add", command=self._add_server_dialog).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(btn_frame, text="- Remove", command=self._remove_server,
                   style='Danger.TButton').pack(side=tk.LEFT)

        list_frame = ttk.Frame(parent, style='Panel.TFrame')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.server_listbox = tk.Listbox(
            list_frame,
            bg='#0f3460',
            fg='#eaeaea',
            selectbackground='#e94560',
            selectforeground='white',
            font=('Consolas', 10),
            borderwidth=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.server_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.server_listbox.yview)
        self.server_listbox.bind('<<ListboxSelect>>', self._on_server_select)

        self.status_label = ttk.Label(parent, text="Status: --", style='Panel.TLabel')
        self.status_label.pack(pady=5, padx=10, anchor='w')

        self.last_seen_label = ttk.Label(parent, text="Last seen: --", style='Panel.TLabel',
                                         wraplength=200)
        self.last_seen_label.pack(pady=2, padx=10, anchor='w')

    def _build_dashboard_tab(self):
        frame = ttk.Frame(self.tab_dashboard)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="SERVER DASHBOARD", style='Header.TLabel').pack(anchor='w', pady=(0, 10))

        metrics_frame = ttk.Frame(frame, style='Panel.TFrame')
        metrics_frame.pack(fill=tk.X, pady=(0, 10))

        cpu_frame = ttk.Frame(metrics_frame, style='Panel.TFrame')
        cpu_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Label(cpu_frame, text="CPU Usage", style='Title.TLabel').pack(anchor='w', padx=5)
        self.cpu_label = ttk.Label(cpu_frame, text="0.0%", style='Panel.TLabel',
                                   font=('Consolas', 20, 'bold'))
        self.cpu_label.pack(padx=5)
        self.cpu_bar = ttk.Progressbar(cpu_frame, length=200, mode='determinate',
                                        style='Horizontal.TProgressbar')
        self.cpu_bar.pack(padx=5, pady=5, fill=tk.X)

        ram_frame = ttk.Frame(metrics_frame, style='Panel.TFrame')
        ram_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Label(ram_frame, text="RAM Usage", style='Title.TLabel').pack(anchor='w', padx=5)
        self.ram_label = ttk.Label(ram_frame, text="0.0%", style='Panel.TLabel',
                                   font=('Consolas', 20, 'bold'))
        self.ram_label.pack(padx=5)
        self.ram_bar = ttk.Progressbar(ram_frame, length=200, mode='determinate',
                                        style='Horizontal.TProgressbar')
        self.ram_bar.pack(padx=5, pady=5, fill=tk.X)
        self.ram_detail_label = ttk.Label(ram_frame, text="0 / 0 GB", style='Panel.TLabel')
        self.ram_detail_label.pack(padx=5)

        net_frame = ttk.Frame(metrics_frame, style='Panel.TFrame')
        net_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Label(net_frame, text="Network", style='Title.TLabel').pack(anchor='w', padx=5)
        self.net_up_label = ttk.Label(net_frame, text="↑ 0 B/s", style='Panel.TLabel')
        self.net_up_label.pack(padx=5, anchor='w')
        self.net_down_label = ttk.Label(net_frame, text="↓ 0 B/s", style='Panel.TLabel')
        self.net_down_label.pack(padx=5, anchor='w')

        if MATPLOTLIB_AVAILABLE:
            self._build_history_charts(frame)
        else:
            ttk.Label(frame, text="Install matplotlib for performance history charts",
                      style='Panel.TLabel').pack(pady=10)

    def _build_history_charts(self, parent):
        chart_frame = ttk.Frame(parent, style='Panel.TFrame')
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(chart_frame, text="Performance History", style='Title.TLabel').pack(anchor='w', padx=5, pady=5)

        self.fig = Figure(figsize=(10, 3), facecolor='#16213e')
        self.ax_cpu = self.fig.add_subplot(121)
        self.ax_ram = self.fig.add_subplot(122)

        for ax in [self.ax_cpu, self.ax_ram]:
            ax.set_facecolor('#0f3460')
            ax.tick_params(colors='#eaeaea', labelsize=8)
            for spine in ax.spines.values():
                spine.set_color('#0f3460')

        self.ax_cpu.set_title('CPU %', color='#e94560', fontsize=9)
        self.ax_ram.set_title('RAM %', color='#e94560', fontsize=9)

        self.canvas_chart = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas_chart.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _build_processes_tab(self):
        frame = ttk.Frame(self.tab_processes)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(top_frame, text="ACTIVE PROCESSES", style='Header.TLabel').pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Refresh", command=self._refresh_processes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_frame, text="Kill Selected", command=self._kill_selected_process,
                   style='Danger.TButton').pack(side=tk.RIGHT, padx=5)

        columns = ('PID', 'Name', 'CPU%', 'MEM%', 'Status', 'User')
        self.process_tree = ttk.Treeview(frame, columns=columns, show='headings', height=25)

        for col in columns:
            self.process_tree.heading(col, text=col,
                                       command=lambda c=col: self._sort_processes(c))
            self.process_tree.column(col, width=120)

        self.process_tree.column('PID', width=70)
        self.process_tree.column('CPU%', width=70)
        self.process_tree.column('MEM%', width=70)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)

        self.process_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_screen_tab(self):
        frame = ttk.Frame(self.tab_screen)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(top_frame, text="REMOTE SCREEN", style='Header.TLabel').pack(side=tk.LEFT)
        self.screen_btn = ttk.Button(top_frame, text="Start Live View",
                                      command=self._toggle_screen_view)
        self.screen_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_frame, text="Capture Once",
                   command=self._capture_once).pack(side=tk.RIGHT, padx=5)

        self.screen_label = tk.Label(frame, bg='#0f3460', text="No screen data",
                                      fg='#eaeaea', font=('Consolas', 12))
        self.screen_label.pack(fill=tk.BOTH, expand=True)

    def _build_tasks_tab(self):
        frame = ttk.Frame(self.tab_tasks)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="TASK MANAGEMENT", style='Header.TLabel').pack(anchor='w', pady=(0, 10))

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(top_frame, text="+ New Task", command=self._add_task_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Complete", command=self._complete_task,
                   style='Success.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Delete", command=self._delete_task,
                   style='Danger.TButton').pack(side=tk.LEFT, padx=5)

        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(filter_frame, text="Filter: ").pack(side=tk.LEFT)
        self.task_filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.task_filter_var,
                                     values=["All", "Pending", "Completed",
                                             "Critical", "High", "Medium", "Low"],
                                     width=15, state='readonly')
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_tasks())

        columns = ('Title', 'Priority', 'Status', 'Server', 'Created')
        self.task_tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)

        for col in columns:
            self.task_tree.heading(col, text=col)
            self.task_tree.column(col, width=150)

        self.task_tree.column('Title', width=250)
        self.task_tree.column('Priority', width=100)
        self.task_tree.column('Status', width=100)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_tasks()

    def _build_agent_tab(self):
        frame = ttk.Frame(self.tab_agent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="AGENT SERVER", style='Header.TLabel').pack(anchor='w', pady=(0, 10))

        info_frame = ttk.Frame(frame, style='Panel.TFrame')
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="Run this on target machines to enable monitoring.",
                  style='Panel.TLabel').pack(padx=10, pady=5, anchor='w')

        config_frame = ttk.Frame(info_frame, style='Panel.TFrame')
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(config_frame, text="Listen Host:", style='Panel.TLabel').grid(row=0, column=0, sticky='w', padx=5)
        self.agent_host_var = tk.StringVar(value='0.0.0.0')
        ttk.Entry(config_frame, textvariable=self.agent_host_var, width=20).grid(row=0, column=1, padx=5)

        ttk.Label(config_frame, text="Listen Port:", style='Panel.TLabel').grid(row=1, column=0, sticky='w', padx=5)
        self.agent_port_var = tk.StringVar(value='9999')
        ttk.Entry(config_frame, textvariable=self.agent_port_var, width=20).grid(row=1, column=1, padx=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        self.agent_start_btn = ttk.Button(btn_frame, text="Start Agent",
                                           command=self._start_agent, style='Success.TButton')
        self.agent_start_btn.pack(side=tk.LEFT, padx=5)
        self.agent_stop_btn = ttk.Button(btn_frame, text="Stop Agent",
                                          command=self._stop_agent, style='Danger.TButton',
                                          state=tk.DISABLED)
        self.agent_stop_btn.pack(side=tk.LEFT, padx=5)

        self.agent_status_label = ttk.Label(frame, text="Agent: Stopped", style='TLabel')
        self.agent_status_label.pack(anchor='w', pady=5)

        log_frame = ttk.Frame(frame, style='Panel.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(log_frame, text="Agent Log", style='Title.TLabel').pack(anchor='w', padx=5, pady=5)
        self.agent_log = scrolledtext.ScrolledText(
            log_frame, bg='#0f3460', fg='#eaeaea', font=('Consolas', 9),
            height=15, state=tk.DISABLED
        )
        self.agent_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.agent_server: Optional[AgentServer] = None

    def _load_servers(self):
        for s_dict in self.datastore.get_servers():
            try:
                server = Server.from_dict(s_dict)
                self.monitoring.add_server(server)
                self._add_server_to_list(server)
                self.monitoring.start_monitoring(server.server_id)
            except Exception as e:
                print(f"[App] Load server error: {e}")

    def _add_server_to_list(self, server: Server):
        self.server_listbox.insert(tk.END, f"  {server.name}")

    def _get_server_at_index(self, index: int) -> Optional[Server]:
        servers = list(self.monitoring.servers.values())
        if 0 <= index < len(servers):
            return servers[index]
        return None

    def _on_server_select(self, event):
        selection = self.server_listbox.curselection()
        if not selection:
            return
        server = self._get_server_at_index(selection[0])
        if server:
            self._selected_server_id = server.server_id
            self._update_server_info(server)
            self._update_dashboard(server)

    def _update_server_info(self, server: Server):
        status_colors = {
            ServerStatus.ONLINE: '#00ff00',
            ServerStatus.OFFLINE: '#ff4444',
            ServerStatus.CONNECTING: '#ffaa00',
            ServerStatus.ERROR: '#ff0000'
        }
        color = status_colors.get(server.status, '#eaeaea')
        self.status_label.config(text=f"Status: {server.status.value.upper()}", foreground=color)
        if server.last_seen:
            try:
                dt = datetime.fromisoformat(server.last_seen)
                self.last_seen_label.config(text=f"Last: {dt.strftime('%H:%M:%S')}")
            except Exception:
                self.last_seen_label.config(text=f"Last: {server.last_seen[:19]}")
        else:
            self.last_seen_label.config(text="Last seen: --")

    def _update_dashboard(self, server: Server):
        if server.metrics:
            m = server.metrics
            self.cpu_label.config(text=f"{m.cpu_percent:.1f}%")
            self.cpu_bar['value'] = m.cpu_percent
            self.ram_label.config(text=f"{m.ram_percent:.1f}%")
            self.ram_bar['value'] = m.ram_percent
            self.ram_detail_label.config(text=f"{m.ram_used_gb:.1f} / {m.ram_total_gb:.1f} GB")
            self.net_up_label.config(text=f"↑ {self._format_bytes(m.net_sent_speed)}/s")
            self.net_down_label.config(text=f"↓ {self._format_bytes(m.net_recv_speed)}/s")

            if MATPLOTLIB_AVAILABLE and hasattr(self, 'ax_cpu'):
                self._update_charts(server)
        else:
            self.cpu_label.config(text="--")
            self.ram_label.config(text="--")
            self.cpu_bar['value'] = 0
            self.ram_bar['value'] = 0

    def _update_charts(self, server: Server):
        history = server.metrics_history
        if not history:
            return

        cpu_data = [m.cpu_percent for m in history]
        ram_data = [m.ram_percent for m in history]
        x = list(range(len(cpu_data)))

        self.ax_cpu.clear()
        self.ax_ram.clear()

        for ax in [self.ax_cpu, self.ax_ram]:
            ax.set_facecolor('#0f3460')
            ax.tick_params(colors='#eaeaea', labelsize=7)
            for spine in ax.spines.values():
                spine.set_color('#0f3460')
            ax.set_ylim(0, 100)

        self.ax_cpu.plot(x, cpu_data, color='#e94560', linewidth=1.5)
        self.ax_cpu.fill_between(x, cpu_data, alpha=0.3, color='#e94560')
        self.ax_cpu.set_title('CPU %', color='#e94560', fontsize=9)

        self.ax_ram.plot(x, ram_data, color='#00aaff', linewidth=1.5)
        self.ax_ram.fill_between(x, ram_data, alpha=0.3, color='#00aaff')
        self.ax_ram.set_title('RAM %', color='#00aaff', fontsize=9)

        self.fig.tight_layout()
        self.canvas_chart.draw()

    def _on_monitoring_event(self, event: str, data: Any):
        if data and hasattr(data, 'server_id') and data.server_id == self._selected_server_id:
            self.root.after(0, self._update_server_info, data)
            if event == "metrics_updated":
                self.root.after(0, self._update_dashboard, data)
        if event == "status_changed":
            self.root.after(0, self._refresh_server_list)

    def _refresh_server_list(self):
        self.server_listbox.delete(0, tk.END)
        for server in self.monitoring.servers.values():
            status_icon = "●" if server.status == ServerStatus.ONLINE else "○"
            self.server_listbox.insert(tk.END, f" {status_icon} {server.name}")

    def _add_server_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Server")
        dialog.geometry("350x250")
        dialog.configure(bg='#1a1a2e')
        dialog.transient(self.root)
        dialog.grab_set()

        fields = {}

        def add_field(label, default=''):
            f = ttk.Frame(dialog)
            f.pack(fill=tk.X, padx=20, pady=5)
            ttk.Label(f, text=label).pack(anchor='w')
            var = tk.StringVar(value=default)
            ttk.Entry(f, textvariable=var).pack(fill=tk.X)
            return var

        ttk.Label(dialog, text="Add New Server", style='Header.TLabel').pack(pady=10)
        fields['name'] = add_field("Server Name:", "My Server")
        fields['host'] = add_field("Host/IP:", "192.168.1.1")
        fields['port'] = add_field("Port:", "9999")

        def confirm():
            name = fields['name'].get().strip()
            host = fields['host'].get().strip()
            try:
                port = int(fields['port'].get().strip())
            except ValueError:
                messagebox.showerror("Error", "Invalid port number", parent=dialog)
                return

            if not name or not host:
                messagebox.showerror("Error", "Name and host are required", parent=dialog)
                return

            server_id = f"srv_{int(time.time() * 1000)}"
            server = Server(server_id=server_id, name=name, host=host, port=port)
            self.monitoring.add_server(server)
            self.datastore.save_server(server)
            self._refresh_server_list()
            self.monitoring.start_monitoring(server_id)
            dialog.destroy()

        ttk.Button(dialog, text="Add Server", command=confirm).pack(pady=10)

    def _remove_server(self):
        selection = self.server_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No server selected")
            return
        server = self._get_server_at_index(selection[0])
        if not server:
            return
        if messagebox.askyesno("Confirm", f"Remove server '{server.name}'?"):
            self.monitoring.remove_server(server.server_id)
            self.datastore.delete_server(server.server_id)
            if self._selected_server_id == server.server_id:
                self._selected_server_id = None
            self._refresh_server_list()

    def _refresh_processes(self):
        if not self._selected_server_id:
            messagebox.showwarning("Warning", "No server selected")
            return

        for item in self.process_tree.get_children():
            self.process_tree.delete(item)

        processes = self.monitoring.get_processes(self._selected_server_id)
        if processes is None:
            messagebox.showerror("Error", "Could not fetch processes. Server may be offline.")
            return

        for proc in processes:
            self.process_tree.insert('', tk.END, values=(
                proc.pid,
                proc.name,
                f"{proc.cpu_percent:.1f}",
                f"{proc.memory_percent:.1f}",
                proc.status,
                proc.username
            ))

    def _sort_processes(self, column: str):
        items = [(self.process_tree.set(item, column), item)
                 for item in self.process_tree.get_children('')]
        try:
            items.sort(key=lambda x: float(x[0]), reverse=True)
        except ValueError:
            items.sort(key=lambda x: x[0])

        for index, (_, item) in enumerate(items):
            self.process_tree.move(item, '', index)

    def _kill_selected_process(self):
        selection = self.process_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No process selected")
            return
        if not self._selected_server_id:
            return

        item = selection[0]
        values = self.process_tree.item(item, 'values')
        pid = int(values[0])
        name = values[1]

        if messagebox.askyesno("Confirm", f"Kill process '{name}' (PID: {pid})?"):
            success = self.monitoring.kill_process(self._selected_server_id, pid)
            if success:
                messagebox.showinfo("Success", f"Process {pid} terminated")
                self._refresh_processes()
            else:
                messagebox.showerror("Error", f"Failed to kill process {pid}")

    def _toggle_screen_view(self):
        if self._screen_update_running:
            self._screen_update_running = False
            self.screen_btn.config(text="Start Live View")
        else:
            if not self._selected_server_id:
                messagebox.showwarning("Warning", "No server selected")
                return
            self._screen_update_running = True
            self.screen_btn.config(text="Stop Live View")
            self._screen_thread = threading.Thread(target=self._screen_loop, daemon=True)
            self._screen_thread.start()

    def _screen_loop(self):
        while self._screen_update_running:
            self._capture_once()
            time.sleep(2.0)

    def _capture_once(self):
        if not self._selected_server_id:
            return
        data = self.monitoring.get_screen(self._selected_server_id)
        if data:
            self.root.after(0, self._display_screen, data)
        else:
            self.root.after(0, lambda: self.screen_label.config(
                text="Screen capture unavailable\n(PIL not installed on agent or capture failed)",
                image=''
            ))

    def _display_screen(self, data: bytes):
        if not PIL_AVAILABLE:
            self.screen_label.config(text="PIL not available for display")
            return
        try:
            img = Image.open(io.BytesIO(data))
            w = self.screen_label.winfo_width() or 800
            h = self.screen_label.winfo_height() or 600
            img.thumbnail((w, h), Image.LANCZOS)
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(img)
            self.screen_label.config(image=photo, text='')
            self.screen_label._photo = photo
        except Exception as e:
            self.screen_label.config(text=f"Display error: {e}", image='')

    def _on_tab_changed(self, event):
        tab = self.notebook.tab(self.notebook.select(), "text")
        if tab == "Screen" and self._screen_update_running:
            pass
        elif tab != "Screen":
            self._screen_update_running = False
            if self.screen_btn.cget('text') == "Stop Live View":
                self.screen_btn.config(text="Start Live View")

    def _add_task_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("New Task")
        dialog.geometry("400x350")
        dialog.configure(bg='#1a1a2e')
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Create New Task", style='Header.TLabel').pack(pady=10)

        f1 = ttk.Frame(dialog)
        f1.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(f1, text="Title:").pack(anchor='w')
        title_var = tk.StringVar()
        ttk.Entry(f1, textvariable=title_var).pack(fill=tk.X)

        f2 = ttk.Frame(dialog)
        f2.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(f2, text="Description:").pack(anchor='w')
        desc_text = tk.Text(f2, height=4, bg='#0f3460', fg='#eaeaea',
                            font=('Consolas', 10), insertbackground='white')
        desc_text.pack(fill=tk.X)

        f3 = ttk.Frame(dialog)
        f3.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(f3, text="Priority:").pack(anchor='w')
        priority_var = tk.StringVar(value='medium')
        priority_combo = ttk.Combobox(f3, textvariable=priority_var,
                                       values=['critical', 'high', 'medium', 'low'],
                                       state='readonly')
        priority_combo.pack(fill=tk.X)

        f4 = ttk.Frame(dialog)
        f4.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(f4, text="Server (optional):").pack(anchor='w')
        server_var = tk.StringVar(value='None')
        server_names = ['None'] + [s.name for s in self.monitoring.servers.values()]
        server_combo = ttk.Combobox(f4, textvariable=server_var,
                                     values=server_names, state='readonly')
        server_combo.pack(fill=tk.X)

        def confirm():
            title = title_var.get().strip()
            if not title:
                messagebox.showerror("Error", "Title is required", parent=dialog)
                return
            desc = desc_text.get('1.0', tk.END).strip()
            priority = TaskPriority(priority_var.get())

            server_id = None
            sel_name = server_var.get()
            if sel_name != 'None':
                for s in self.monitoring.servers.values():
                    if s.name == sel_name:
                        server_id = s.server_id
                        break

            self.task_manager.create_task(title, desc, priority, server_id)
            self._refresh_tasks()
            dialog.destroy()

        ttk.Button(dialog, text="Create Task", command=confirm).pack(pady=10)

    def _complete_task(self):
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No task selected")
            return
        item = selection[0]
        task_id = self.task_tree.item(item, 'tags')[0] if self.task_tree.item(item, 'tags') else None
        if task_id:
            self.task_manager.complete_task(task_id)
            self._refresh_tasks()

    def _delete_task(self):
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No task selected")
            return
        item = selection[0]
        tags = self.task_tree.item(item, 'tags')
        task_id = tags[0] if tags else None
        if task_id and messagebox.askyesno("Confirm", "Delete this task?"):
            self.task_manager.delete_task(task_id)
            self._refresh_tasks()

    def _refresh_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        filter_val = self.task_filter_var.get() if hasattr(self, 'task_filter_var') else "All"

        completed = None
        priority_filter = None

        if filter_val == "Pending":
            completed = False
        elif filter_val == "Completed":
            completed = True
        elif filter_val in ["Critical", "High", "Medium", "Low"]:
            priority_filter = TaskPriority(filter_val.lower())

        tasks = self.task_manager.get_tasks(completed=completed, priority=priority_filter)

        priority_colors = {
            TaskPriority.CRITICAL: '#ff4444',
            TaskPriority.HIGH: '#ff8800',
            TaskPriority.MEDIUM: '#ffcc00',
            TaskPriority.LOW: '#88cc88'
        }

        for task in tasks:
            server_name = ""
            if task.server_id and task.server_id in self.monitoring.servers:
                server_name = self.monitoring.servers[task.server_id].name

            status = "✓ Done" if task.completed else "Pending"
            item = self.task_tree.insert('', tk.END, values=(
                task.title,
                task.priority.value.upper(),
                status,
                server_name,
                task.created_at[:10]
            ), tags=(task.task_id,))

            color = priority_colors.get(task.priority, '#eaeaea')
            self.task_tree.tag_configure(task.task_id, foreground=color)

    def _start_agent(self):
        try:
            host = self.agent_host_var.get().strip()
            port = int(self.agent_port_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return

        self.agent_server = AgentServer(host=host, port=port)
        self.agent_server.start()
        self.agent_status_label.config(text=f"Agent: Running on {host}:{port}", foreground='#00ff00')
        self.agent_start_btn.config(state=tk.DISABLED)
        self.agent_stop_btn.config(state=tk.NORMAL)
        self._log_agent(f"Agent started on {host}:{port}")

    def _stop_agent(self):
        if self.agent_server:
            self.agent_server.stop()
            self.agent_server = None
        self.agent_status_label.config(text="Agent: Stopped", foreground='#ff4444')
        self.agent_start_btn.config(state=tk.NORMAL)
        self.agent_stop_btn.config(state=tk.DISABLED)
        self._log_agent("Agent stopped")

    def _log_agent(self, message: str):
        self.agent_log.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.agent_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.agent_log.see(tk.END)
        self.agent_log.config(state=tk.DISABLED)

    @staticmethod
    def _format_bytes(b: float) -> str:
        if b < 1024:
            return f"{b:.0f} B"
        elif b < 1024 ** 2:
            return f"{b / 1024:.1f} KB"
        elif b < 1024 ** 3:
            return f"{b / (1024 ** 2):.1f} MB"
        else:
            return f"{b / (1024 ** 3):.1f} GB"

    def _on_close(self):
        self._screen_update_running = False
        for server_id in list(self.monitoring.servers.keys()):
            self.monitoring.stop_monitoring(server_id)
        if self.agent_server:
            self.agent_server.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_agent_mode(host: str = '0.0.0.0', port: int = 9999):
    print(f"[NexusCtrl Agent] Starting on {host}:{port}")
    agent = AgentServer(host=host, port=port)
    agent.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[NexusCtrl Agent] Stopping...")
        agent.stop()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--agent':
        host = sys.argv[2] if len(sys.argv) > 2 else '0.0.0.0'
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
        run_agent_mode(host, port)
    else:
        app = NexusCtrlApp()
        app.run()


if __name__ == '__main__':
    main()