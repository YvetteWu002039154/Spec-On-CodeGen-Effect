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

try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

try:
    from PIL import Image, ImageTk, ImageGrab
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageTk, ImageGrab


class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "server_id": self.server_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            task_id=data["task_id"],
            title=data["title"],
            description=data["description"],
            priority=TaskPriority(data["priority"]),
            completed=data.get("completed", False),
            created_at=data.get("created_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
            server_id=data.get("server_id"),
        )


@dataclass
class ServerMetrics:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    net_bytes_sent: int = 0
    net_bytes_recv: int = 0
    net_sent_speed: float = 0.0
    net_recv_speed: float = 0.0
    processes: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PerformanceHistory:
    cpu_history: List[float] = field(default_factory=list)
    ram_history: List[float] = field(default_factory=list)
    net_sent_history: List[float] = field(default_factory=list)
    net_recv_history: List[float] = field(default_factory=list)
    timestamps: List[str] = field(default_factory=list)
    max_entries: int = 60

    def add_metrics(self, metrics: ServerMetrics):
        self.cpu_history.append(metrics.cpu_percent)
        self.ram_history.append(metrics.ram_percent)
        self.net_sent_history.append(metrics.net_sent_speed)
        self.net_recv_history.append(metrics.net_recv_speed)
        self.timestamps.append(metrics.timestamp)

        if len(self.cpu_history) > self.max_entries:
            self.cpu_history.pop(0)
            self.ram_history.pop(0)
            self.net_sent_history.pop(0)
            self.net_recv_history.pop(0)
            self.timestamps.pop(0)


@dataclass
class Server:
    server_id: str
    name: str
    host: str
    port: int
    status: ServerStatus = ServerStatus.OFFLINE
    metrics: ServerMetrics = field(default_factory=ServerMetrics)
    history: PerformanceHistory = field(default_factory=PerformanceHistory)
    last_seen: Optional[str] = None
    screen_data: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Server":
        return cls(
            server_id=data["server_id"],
            name=data["name"],
            host=data["host"],
            port=data["port"],
        )


class AgentProtocol:
    HEADER_SIZE = 8
    MSG_METRICS = 0x01
    MSG_SCREEN = 0x02
    MSG_KILL_PROCESS = 0x03
    MSG_KILL_ACK = 0x04
    MSG_PING = 0x05
    MSG_PONG = 0x06

    @staticmethod
    def pack_message(msg_type: int, data: bytes) -> bytes:
        header = struct.pack("!II", msg_type, len(data))
        return header + data

    @staticmethod
    def unpack_header(header: bytes) -> tuple:
        return struct.unpack("!II", header)

    @staticmethod
    def recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
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


class AgentServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self._prev_net = psutil.net_io_counters()
        self._prev_net_time = time.time()

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"[Agent] Listening on {self.host}:{self.port}")

        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                try:
                    conn, addr = self.server_socket.accept()
                    print(f"[Agent] Connection from {addr}")
                    t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:
                    print(f"[Agent] Error: {e}")
                break

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

    def _collect_metrics(self) -> Dict[str, Any]:
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

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'] or "",
                    "cpu_percent": info['cpu_percent'] or 0.0,
                    "memory_percent": round(info['memory_percent'] or 0.0, 2),
                    "status": info['status'] or "",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "cpu_percent": cpu,
            "ram_percent": ram.percent,
            "ram_used_mb": ram.used / (1024 * 1024),
            "ram_total_mb": ram.total / (1024 * 1024),
            "net_bytes_sent": net.bytes_sent,
            "net_bytes_recv": net.bytes_recv,
            "net_sent_speed": sent_speed,
            "net_recv_speed": recv_speed,
            "processes": processes,
            "timestamp": datetime.now().isoformat(),
        }

    def _capture_screen(self) -> bytes:
        try:
            img = ImageGrab.grab()
            img = img.resize((800, 600), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50)
            return buf.getvalue()
        except Exception as e:
            print(f"[Agent] Screen capture error: {e}")
            img = Image.new("RGB", (800, 600), color=(30, 30, 30))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50)
            return buf.getvalue()

    def _handle_client(self, conn: socket.socket):
        conn.settimeout(30)
        try:
            while True:
                header = AgentProtocol.recv_exact(conn, AgentProtocol.HEADER_SIZE)
                if not header:
                    break
                msg_type, data_len = AgentProtocol.unpack_header(header)

                if data_len > 0:
                    data = AgentProtocol.recv_exact(conn, data_len)
                    if data is None:
                        break
                else:
                    data = b""

                if msg_type == AgentProtocol.MSG_PING:
                    metrics = self._collect_metrics()
                    metrics_json = json.dumps(metrics).encode()
                    msg = AgentProtocol.pack_message(AgentProtocol.MSG_METRICS, metrics_json)
                    conn.sendall(msg)

                    screen = self._capture_screen()
                    screen_msg = AgentProtocol.pack_message(AgentProtocol.MSG_SCREEN, screen)
                    conn.sendall(screen_msg)

                elif msg_type == AgentProtocol.MSG_KILL_PROCESS:
                    pid = int(data.decode())
                    success = self._kill_process(pid)
                    ack_data = json.dumps({"success": success, "pid": pid}).encode()
                    msg = AgentProtocol.pack_message(AgentProtocol.MSG_KILL_ACK, ack_data)
                    conn.sendall(msg)

        except Exception as e:
            print(f"[Agent] Client handler error: {e}")
        finally:
            conn.close()

    def _kill_process(self, pid: int) -> bool:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=3)
            return True
        except psutil.NoSuchProcess:
            return True
        except Exception as e:
            print(f"[Agent] Kill process error: {e}")
            try:
                proc = psutil.Process(pid)
                proc.kill()
                return True
            except Exception:
                return False


class ServerConnection:
    def __init__(self, server: Server):
        self.server = server
        self.socket: Optional[socket.socket] = None
        self.lock = threading.Lock()

    def connect(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.server.host, self.server.port))
            self.socket = s
            return True
        except Exception as e:
            print(f"[Controller] Connect error to {self.server.name}: {e}")
            self.socket = None
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def fetch_metrics_and_screen(self) -> bool:
        with self.lock:
            if not self.socket:
                if not self.connect():
                    return False
            try:
                ping = AgentProtocol.pack_message(AgentProtocol.MSG_PING, b"")
                self.socket.sendall(ping)

                header = AgentProtocol.recv_exact(self.socket, AgentProtocol.HEADER_SIZE)
                if not header:
                    self.disconnect()
                    return False
                msg_type, data_len = AgentProtocol.unpack_header(header)
                if msg_type != AgentProtocol.MSG_METRICS:
                    self.disconnect()
                    return False
                data = AgentProtocol.recv_exact(self.socket, data_len)
                if not data:
                    self.disconnect()
                    return False
                metrics_dict = json.loads(data.decode())
                m = self.server.metrics
                m.cpu_percent = metrics_dict["cpu_percent"]
                m.ram_percent = metrics_dict["ram_percent"]
                m.ram_used_mb = metrics_dict["ram_used_mb"]
                m.ram_total_mb = metrics_dict["ram_total_mb"]
                m.net_bytes_sent = metrics_dict["net_bytes_sent"]
                m.net_bytes_recv = metrics_dict["net_bytes_recv"]
                m.net_sent_speed = metrics_dict["net_sent_speed"]
                m.net_recv_speed = metrics_dict["net_recv_speed"]
                m.processes = metrics_dict["processes"]
                m.timestamp = metrics_dict["timestamp"]
                self.server.history.add_metrics(m)
                self.server.last_seen = datetime.now().isoformat()

                header2 = AgentProtocol.recv_exact(self.socket, AgentProtocol.HEADER_SIZE)
                if not header2:
                    self.disconnect()
                    return False
                msg_type2, data_len2 = AgentProtocol.unpack_header(header2)
                if msg_type2 != AgentProtocol.MSG_SCREEN:
                    self.disconnect()
                    return False
                screen_data = AgentProtocol.recv_exact(self.socket, data_len2)
                if screen_data:
                    self.server.screen_data = screen_data

                return True
            except Exception as e:
                print(f"[Controller] Fetch error for {self.server.name}: {e}")
                self.disconnect()
                return False

    def kill_process(self, pid: int) -> bool:
        with self.lock:
            if not self.socket:
                if not self.connect():
                    return False
            try:
                data = str(pid).encode()
                msg = AgentProtocol.pack_message(AgentProtocol.MSG_KILL_PROCESS, data)
                self.socket.sendall(msg)

                header = AgentProtocol.recv_exact(self.socket, AgentProtocol.HEADER_SIZE)
                if not header:
                    self.disconnect()
                    return False
                msg_type, data_len = AgentProtocol.unpack_header(header)
                if msg_type != AgentProtocol.MSG_KILL_ACK:
                    self.disconnect()
                    return False
                ack_data = AgentProtocol.recv_exact(self.socket, data_len)
                if not ack_data:
                    self.disconnect()
                    return False
                result = json.loads(ack_data.decode())
                return result.get("success", False)
            except Exception as e:
                print(f"[Controller] Kill process error: {e}")
                self.disconnect()
                return False


class TaskManager:
    def __init__(self, data_file: str = "tasks.json"):
        self.data_file = data_file
        self.tasks: Dict[str, Task] = {}
        self._counter = 0
        self.load()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"task_{int(time.time())}_{self._counter}"

    def create_task(self, title: str, description: str, priority: TaskPriority,
                    server_id: Optional[str] = None) -> Task:
        task = Task(
            task_id=self._generate_id(),
            title=title,
            description=description,
            priority=priority,
            server_id=server_id,
        )
        self.tasks[task.task_id] = task
        self.save()
        return task

    def complete_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id].completed = True
            self.tasks[task_id].completed_at = datetime.now().isoformat()
            self.save()
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save()
            return True
        return False

    def get_tasks(self, server_id: Optional[str] = None,
                  completed: Optional[bool] = None) -> List[Task]:
        tasks = list(self.tasks.values())
        if server_id is not None:
            tasks = [t for t in tasks if t.server_id == server_id]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }
        tasks.sort(key=lambda t: priority_order.get(t.priority, 99))
        return tasks

    def save(self):
        try:
            data = {tid: task.to_dict() for tid, task in self.tasks.items()}
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[TaskManager] Save error: {e}")

    def load(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                self.tasks = {tid: Task.from_dict(td) for tid, td in data.items()}
        except Exception as e:
            print(f"[TaskManager] Load error: {e}")


class ServerManager:
    def __init__(self, data_file: str = "servers.json"):
        self.data_file = data_file
        self.servers: Dict[str, Server] = {}
        self.connections: Dict[str, ServerConnection] = {}
        self._counter = 0
        self.load()

    def _generate_id(self) -> str:
        self._counter += 1
        return f"server_{int(time.time())}_{self._counter}"

    def add_server(self, name: str, host: str, port: int) -> Server:
        server = Server(
            server_id=self._generate_id(),
            name=name,
            host=host,
            port=port,
        )
        self.servers[server.server_id] = server
        self.connections[server.server_id] = ServerConnection(server)
        self.save()
        return server

    def remove_server(self, server_id: str) -> bool:
        if server_id in self.servers:
            if server_id in self.connections:
                self.connections[server_id].disconnect()
                del self.connections[server_id]
            del self.servers[server_id]
            self.save()
            return True
        return False

    def get_server(self, server_id: str) -> Optional[Server]:
        return self.servers.get(server_id)

    def get_all_servers(self) -> List[Server]:
        return list(self.servers.values())

    def fetch_server_data(self, server_id: str) -> bool:
        if server_id not in self.connections:
            return False
        conn = self.connections[server_id]
        success = conn.fetch_metrics_and_screen()
        server = self.servers.get(server_id)
        if server:
            server.status = ServerStatus.ONLINE if success else ServerStatus.OFFLINE
        return success

    def kill_process(self, server_id: str, pid: int) -> bool:
        if server_id not in self.connections:
            return False
        return self.connections[server_id].kill_process(pid)

    def save(self):
        try:
            data = {sid: s.to_dict() for sid, s in self.servers.items()}
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ServerManager] Save error: {e}")

    def load(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                for sid, sd in data.items():
                    server = Server.from_dict(sd)
                    self.servers[sid] = server
                    self.connections[sid] = ServerConnection(server)
        except Exception as e:
            print(f"[ServerManager] Load error: {e}")


class MonitoringThread(threading.Thread):
    def __init__(self, server_manager: ServerManager, interval: float = 3.0):
        super().__init__(daemon=True)
        self.server_manager = server_manager
        self.interval = interval
        self.running = False
        self.callbacks: List[Any] = []

    def add_callback(self, cb):
        self.callbacks.append(cb)

    def run(self):
        self.running = True
        while self.running:
            for server_id in list(self.server_manager.servers.keys()):
                self.server_manager.fetch_server_data(server_id)
            for cb in self.callbacks:
                try:
                    cb()
                except Exception as e:
                    print(f"[Monitor] Callback error: {e}")
            time.sleep(self.interval)

    def stop(self):
        self.running = False


class AddServerDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Server")
        self.resizable(False, False)
        self.result = None
        self._build()
        self.grab_set()
        self.wait_window()

    def _build(self):
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Server Name:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.name_var, width=30).grid(row=0, column=1, pady=4, padx=5)

        ttk.Label(frame, text="Host/IP:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(frame, textvariable=self.host_var, width=30).grid(row=1, column=1, pady=4, padx=5)

        ttk.Label(frame, text="Port:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.port_var = tk.StringVar(value="9999")
        ttk.Entry(frame, textvariable=self.port_var, width=30).grid(row=2, column=1, pady=4, padx=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Add", command=self._on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _on_add(self):
        name = self.name_var.get().strip()
        host = self.host_var.get().strip()
        port_str = self.port_var.get().strip()
        if not name or not host or not port_str:
            messagebox.showerror("Error", "All fields are required.", parent=self)
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.", parent=self)
            return
        self.result = (name, host, port)
        self.destroy()


class AddTaskDialog(tk.Toplevel):
    def __init__(self, parent, servers: List[Server]):
        super().__init__(parent)
        self.title("Add Task")
        self.resizable(False, False)
        self.result = None
        self.servers = servers
        self._build()
        self.grab_set()
        self.wait_window()

    def _build(self):
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.title_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.title_var, width=35).grid(row=0, column=1, pady=4, padx=5)

        ttk.Label(frame, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.desc_text = tk.Text(frame, width=35, height=4)
        self.desc_text.grid(row=1, column=1, pady=4, padx=5)

        ttk.Label(frame, text="Priority:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.priority_var = tk.StringVar(value="medium")
        priority_combo = ttk.Combobox(frame, textvariable=self.priority_var, width=32,
                                      values=["critical", "high", "medium", "low"], state="readonly")
        priority_combo.grid(row=2, column=1, pady=4, padx=5)

        ttk.Label(frame, text="Server (optional):").grid(row=3, column=0, sticky=tk.W, pady=4)
        server_names = ["None"] + [s.name for s in self.servers]
        self.server_var = tk.StringVar(value="None")
        ttk.Combobox(frame, textvariable=self.server_var, width=32,
                     values=server_names, state="readonly").grid(row=3, column=1, pady=4, padx=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Create", command=self._on_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _on_create(self):
        title = self.title_var.get().strip()
        desc = self.desc_text.get("1.0", tk.END).strip()
        priority_str = self.priority_var.get()
        server_name = self.server_var.get()

        if not title:
            messagebox.showerror("Error", "Title is required.", parent=self)
            return

        server_id = None
        if server_name != "None":
            for s in self.servers:
                if s.name == server_name:
                    server_id = s.server_id
                    break

        self.result = (title, desc, TaskPriority(priority_str), server_id)
        self.destroy()


class HistoryCanvas(tk.Canvas):
    def __init__(self, parent, label: str, color: str, **kwargs):
        super().__init__(parent, bg="#1e1e2e", **kwargs)
        self.label = label
        self.color = color
        self.data: List[float] = []
        self.bind("<Configure>", self._on_resize)

    def update_data(self, data: List[float]):
        self.data = data[:]
        self._draw()

    def _on_resize(self, event):
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2:
            return

        self.create_text(5, 5, anchor=tk.NW, text=self.label, fill="white", font=("Consolas", 9))

        if not self.data:
            return

        max_val = max(self.data) if max(self.data) > 0 else 100
        max_val = max(max_val, 1)

        pad_top = 20
        pad_bottom = 5
        pad_left = 5
        pad_right = 5
        graph_w = w - pad_left - pad_right
        graph_h = h - pad_top - pad_bottom

        n = len(self.data)
        if n < 2:
            return

        points = []
        for i, val in enumerate(self.data):
            x = pad_left + (i / (n - 1)) * graph_w
            y = pad_top + graph_h - (val / max_val) * graph_h
            points.append((x, y))

        for i in range(len(points) - 1):
            self.create_line(points[i][0], points[i][1],
                             points[i + 1][0], points[i + 1][1],
                             fill=self.color, width=2)

        last_val = self.data[-1]
        self.create_text(w - pad_right, pad_top, anchor=tk.NE,
                         text=f"{last_val:.1f}%", fill=self.color, font=("Consolas", 9))


class ServerDetailPanel(ttk.Frame):
    def __init__(self, parent, server_manager: ServerManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.server_manager = server_manager
        self.current_server_id: Optional[str] = None
        self._build()

    def _build(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Overview")
        self._build_overview()

        self.processes_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.processes_frame, text="Processes")
        self._build_processes()

        self.screen_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.screen_frame, text="Screen")
        self._build_screen()

        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="History")
        self._build_history()

    def _build_overview(self):
        frame = ttk.Frame(self.overview_frame, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        self.server_name_label = ttk.Label(frame, text="No server selected",
                                           font=("Consolas", 14, "bold"))
        self.server_name_label.pack(anchor=tk.W)

        self.status_label = ttk.Label(frame, text="Status: --", font=("Consolas", 10))
        self.status_label.pack(anchor=tk.W, pady=2)

        metrics_frame = ttk.LabelFrame(frame, text="Current Metrics", padding=10)
        metrics_frame.pack(fill=tk.X, pady=10)

        self.cpu_label = ttk.Label(metrics_frame, text="CPU: --", font=("Consolas", 11))
        self.cpu_label.pack(anchor=tk.W)
        self.cpu_bar = ttk.Progressbar(metrics_frame, length=300, maximum=100)
        self.cpu_bar.pack(anchor=tk.W, pady=2)

        self.ram_label = ttk.Label(metrics_frame, text="RAM: --", font=("Consolas", 11))
        self.ram_label.pack(anchor=tk.W, pady=(8, 0))
        self.ram_bar = ttk.Progressbar(metrics_frame, length=300, maximum=100)
        self.ram_bar.pack(anchor=tk.W, pady=2)

        self.net_label = ttk.Label(metrics_frame, text="Network: --", font=("Consolas", 11))
        self.net_label.pack(anchor=tk.W, pady=(8, 0))

        self.last_seen_label = ttk.Label(frame, text="Last seen: --", font=("Consolas", 9))
        self.last_seen_label.pack(anchor=tk.W, pady=5)

    def _build_processes(self):
        frame = ttk.Frame(self.processes_frame, padding=5)
        frame.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Filter:").pack(side=tk.LEFT)
        self.proc_filter_var = tk.StringVar()
        self.proc_filter_var.trace("w", self._filter_processes)
        ttk.Entry(search_frame, textvariable=self.proc_filter_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Kill Selected", command=self._kill_selected_process).pack(side=tk.RIGHT)

        cols = ("PID", "Name", "CPU%", "MEM%", "Status")
        self.proc_tree = ttk.Treeview(frame, columns=cols, show="headings", height=15)
        for col in cols:
            self.proc_tree.heading(col, text=col)
            self.proc_tree.column(col, width=100)
        self.proc_tree.column("PID", width=70)
        self.proc_tree.column("Name", width=200)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=scrollbar.set)
        self.proc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._all_processes: List[Dict] = []

    def _build_screen(self):
        frame = ttk.Frame(self.screen_frame)
        frame.pack(fill=tk.BOTH, expand=True)

        self.screen_label = ttk.Label(frame, text="No screen data available")
        self.screen_label.pack(expand=True)
        self._screen_image = None

    def _build_history(self):
        frame = ttk.Frame(self.history_frame, padding=5)
        frame.pack(fill=tk.BOTH, expand=True)

        self.cpu_canvas = HistoryCanvas(frame, "CPU %", "#00ff88", height=100)
        self.cpu_canvas.pack(fill=tk.X, pady=5)

        self.ram_canvas = HistoryCanvas(frame, "RAM %", "#ff8800", height=100)
        self.ram_canvas.pack(fill=tk.X, pady=5)

        self.net_sent_canvas = HistoryCanvas(frame, "Net Sent KB/s", "#00aaff", height=100)
        self.net_sent_canvas.pack(fill=tk.X, pady=5)

        self.net_recv_canvas = HistoryCanvas(frame, "Net Recv KB/s", "#ff00aa", height=100)
        self.net_recv_canvas.pack(fill=tk.X, pady=5)

    def set_server(self, server_id: Optional[str]):
        self.current_server_id = server_id
        self.refresh()

    def refresh(self):
        if not self.current_server_id:
            return
        server = self.server_manager.get_server(self.current_server_id)
        if not server:
            return

        self.server_name_label.config(text=server.name)
        status_color = "green" if server.status == ServerStatus.ONLINE else "red"
        self.status_label.config(text=f"Status: {server.status.value.upper()}")

        m = server.metrics
        self.cpu_label.config(text=f"CPU: {m.cpu_percent:.1f}%")
        self.cpu_bar["value"] = m.cpu_percent

        self.ram_label.config(
            text=f"RAM: {m.ram_percent:.1f}% ({m.ram_used_mb:.0f} MB / {m.ram_total_mb:.0f} MB)")
        self.ram_bar["value"] = m.ram_percent

        sent_kb = m.net_sent_speed / 1024
        recv_kb = m.net_recv_speed / 1024
        self.net_label.config(text=f"Network: ↑ {sent_kb:.1f} KB/s  ↓ {recv_kb:.1f} KB/s")

        if server.last_seen:
            self.last_seen_label.config(text=f"Last seen: {server.last_seen}")

        self._all_processes = m.processes
        self._filter_processes()

        if server.screen_data:
            try:
                img = Image.open(io.BytesIO(server.screen_data))
                img = img.resize((780, 500), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.screen_label.config(image=photo, text="")
                self._screen_image = photo
            except Exception as e:
                self.screen_label.config(text=f"Screen error: {e}", image="")

        h = server.history
        self.cpu_canvas.update_data(h.cpu_history)
        self.ram_canvas.update_data(h.ram_history)
        net_sent_kb = [v / 1024 for v in h.net_sent_history]
        net_recv_kb = [v / 1024 for v in h.net_recv_history]
        self.net_sent_canvas.update_data(net_sent_kb)
        self.net_recv_canvas.update_data(net_recv_kb)

    def _filter_processes(self, *args):
        filter_text = self.proc_filter_var.get().lower()
        for item in self.proc_tree.get_children():
            self.proc_tree.delete(item)
        for proc in self._all_processes:
            name = proc.get("name", "").lower()
            if filter_text and filter_text not in name and filter_text not in str(proc.get("pid", "")):
                continue
            self.proc_tree.insert("", tk.END, values=(
                proc.get("pid", ""),
                proc.get("name", ""),
                f"{proc.get('cpu_percent', 0):.1f}",
                f"{proc.get('memory_percent', 0):.2f}",
                proc.get("status", ""),
            ))

    def _kill_selected_process(self):
        if not self.current_server_id:
            return
        selected = self.proc_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "No process selected.")
            return
        item = self.proc_tree.item(selected[0])
        pid = item["values"][0]
        name = item["values"][1]
        if messagebox.askyesno("Confirm", f"Kill process {name} (PID: {pid})?"):
            success = self.server_manager.kill_process(self.current_server_id, int(pid))
            if success:
                messagebox.showinfo("Success", f"Process {pid} terminated.")
            else:
                messagebox.showerror("Error", f"Failed to kill process {pid}.")


class TaskPanel(ttk.Frame):
    def __init__(self, parent, task_manager: TaskManager, server_manager: ServerManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.task_manager = task_manager
        self.server_manager = server_manager
        self._build()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=5, padx=5)

        ttk.Button(toolbar, text="+ New Task", command=self._add_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Complete", command=self._complete_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_task).pack(side=tk.LEFT, padx=2)

        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(filter_frame, text="Show:").pack(side=tk.LEFT)
        self.show_var = tk.StringVar(value="all")
        ttk.Radiobutton(filter_frame, text="All", variable=self.show_var,
                        value="all", command=self.refresh).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Pending", variable=self.show_var,
                        value="pending", command=self.refresh).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Completed", variable=self.show_var,
                        value="completed", command=self.refresh).pack(side=tk.LEFT)

        cols = ("Priority", "Title", "Server", "Status", "Created")
        self.task_tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        for col in cols:
            self.task_tree.heading(col, text=col)
        self.task_tree.column("Priority", width=80)
        self.task_tree.column("Title", width=200)
        self.task_tree.column("Server", width=120)
        self.task_tree.column("Status", width=80)
        self.task_tree.column("Created", width=150)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._task_ids: List[str] = []
        self.refresh()

    def refresh(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        self._task_ids = []

        show = self.show_var.get()
        completed_filter = None
        if show == "pending":
            completed_filter = False
        elif show == "completed":
            completed_filter = True

        tasks = self.task_manager.get_tasks(completed=completed_filter)
        servers = {s.server_id: s.name for s in self.server_manager.get_all_servers()}

        priority_colors = {
            TaskPriority.CRITICAL: "#ff4444",
            TaskPriority.HIGH: "#ff8800",
            TaskPriority.MEDIUM: "#ffff00",
            TaskPriority.LOW: "#aaaaaa",
        }

        for task in tasks:
            server_name = servers.get(task.server_id, "General") if task.server_id else "General"
            status = "Done" if task.completed else "Pending"
            created = task.created_at[:10] if task.created_at else ""
            self.task_tree.insert("", tk.END, values=(
                task.priority.value.upper(),
                task.title,
                server_name,
                status,
                created,
            ))
            self._task_ids.append(task.task_id)

    def _get_selected_task_id(self) -> Optional[str]:
        selected = self.task_tree.selection()
        if not selected:
            return None
        idx = self.task_tree.index(selected[0])
        if idx < len(self._task_ids):
            return self._task_ids[idx]
        return None

    def _add_task(self):
        servers = self.server_manager.get_all_servers()
        dialog = AddTaskDialog(self, servers)
        if dialog.result:
            title, desc, priority, server_id = dialog.result
            self.task_manager.create_task(title, desc, priority, server_id)
            self.refresh()

    def _complete_task(self):
        task_id = self._get_selected_task_id()
        if not task_id:
            messagebox.showinfo("Info", "No task selected.")
            return
        self.task_manager.complete_task(task_id)
        self.refresh()

    def _delete_task(self):
        task_id = self._get_selected_task_id()
        if not task_id:
            messagebox.showinfo("Info", "No task selected.")
            return
        if messagebox.askyesno("Confirm", "Delete this task?"):
            self.task_manager.delete_task(task_id)
            self.refresh()


class NexusCtrlApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NexusCtrl - RDP Server Management")
        self.geometry("1200x750")
        self.configure(bg="#1e1e2e")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4")
        style.configure("TButton", background="#313244", foreground="#cdd6f4")
        style.configure("TNotebook", background="#1e1e2e")
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4")
        style.configure("Treeview", background="#181825", foreground="#cdd6f4",
                        fieldbackground="#181825")
        style.configure("Treeview.Heading", background="#313244", foreground="#cdd6f4")
        style.configure("TLabelframe", background="#1e1e2e", foreground="#cdd6f4")
        style.configure("TLabelframe.Label", background="#1e1e2e", foreground="#cdd6f4")
        style.configure("TProgressbar", background="#00ff88")
        style.configure("TRadiobutton", background="#1e1e2e", foreground="#cdd6f4")

        self.server_manager = ServerManager()
        self.task_manager = TaskManager()

        self.monitor_thread = MonitoringThread(self.server_manager, interval=3.0)
        self.monitor_thread.add_callback(self._on_monitor_update)
        self.monitor_thread.start()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_pane, width=220)
        main_pane.add(left_frame, weight=0)

        right_notebook = ttk.Notebook(main_pane)
        main_pane.add(right_notebook, weight=1)

        self._build_server_list(left_frame)

        self.detail_panel = ServerDetailPanel(right_notebook, self.server_manager)
        right_notebook.add(self.detail_panel, text="Server Monitor")

        self.task_panel = TaskPanel(right_notebook, self.task_manager, self.server_manager)
        right_notebook.add(self.task_panel, text="Tasks")

        self._build_agent_tab(right_notebook)

    def _build_server_list(self, parent):
        ttk.Label(parent, text="SERVERS", font=("Consolas", 11, "bold")).pack(pady=5)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5)
        ttk.Button(btn_frame, text="+ Add", command=self._add_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self._remove_server).pack(side=tk.LEFT, padx=2)

        self.server_listbox = tk.Listbox(parent, bg="#181825", fg="#cdd6f4",
                                         selectbackground="#313244", font=("Consolas", 10),
                                         height=20)
        self.server_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.server_listbox.bind("<<ListboxSelect>>", self._on_server_select)

        self._server_ids: List[str] = []
        self._refresh_server_list()

    def _build_agent_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="Agent")

        ttk.Label(frame, text="Run Agent on This Machine",
                  font=("Consolas", 13, "bold")).pack(pady=10)

        config_frame = ttk.LabelFrame(frame, text="Agent Configuration", padding=10)
        config_frame.pack(fill=tk.X, pady=10)

        ttk.Label(config_frame, text="Listen Port:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.agent_port_var = tk.StringVar(value="9999")
        ttk.Entry(config_frame, textvariable=self.agent_port_var, width=15).grid(row=0, column=1, padx=5)

        self.agent_status_label = ttk.Label(frame, text="Agent: Stopped", font=("Consolas", 11))
        self.agent_status_label.pack(pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        self.start_agent_btn = ttk.Button(btn_frame, text="Start Agent", command=self._start_agent)
        self.start_agent_btn.pack(side=tk.LEFT, padx=5)
        self.stop_agent_btn = ttk.Button(btn_frame, text="Stop Agent", command=self._stop_agent,
                                         state=tk.DISABLED)
        self.stop_agent_btn.pack(side=tk.LEFT, padx=5)

        info_frame = ttk.LabelFrame(frame, text="Agent Info", padding=10)
        info_frame.pack(fill=tk.X, pady=10)

        local_ip = self._get_local_ip()
        ttk.Label(info_frame, text=f"Local IP: {local_ip}", font=("Consolas", 10)).pack(anchor=tk.W)
        ttk.Label(info_frame, text="The agent collects CPU, RAM, network metrics,",
                  font=("Consolas", 9)).pack(anchor=tk.W)
        ttk.Label(info_frame, text="captures screen, and responds to remote commands.",
                  font=("Consolas", 9)).pack(anchor=tk.W)

        self._agent_server: Optional[AgentServer] = None
        self._agent_thread: Optional[threading.Thread] = None

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _start_agent(self):
        try:
            port = int(self.agent_port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return

        self._agent_server = AgentServer(host="0.0.0.0", port=port)
        self._agent_thread = threading.Thread(target=self._agent_server.start, daemon=True)
        self._agent_thread.start()
        self.agent_status_label.config(text=f"Agent: Running on port {port}")
        self.start_agent_btn.config(state=tk.DISABLED)
        self.stop_agent_btn.config(state=tk.NORMAL)

    def _stop_agent(self):
        if self._agent_server:
            self._agent_server.stop()
            self._agent_server = None
        self.agent_status_label.config(text="Agent: Stopped")
        self.start_agent_btn.config(state=tk.NORMAL)
        self.stop_agent_btn.config(state=tk.DISABLED)

    def _refresh_server_list(self):
        self.server_listbox.delete(0, tk.END)
        self._server_ids = []
        for server in self.server_manager.get_all_servers():
            status_icon = "●" if server.status == ServerStatus.ONLINE else "○"
            self.server_listbox.insert(tk.END, f"{status_icon} {server.name} ({server.host}:{server.port})")
            self._server_ids.append(server.server_id)

    def _on_server_select(self, event):
        selected = self.server_listbox.curselection()
        if not selected:
            return
        idx = selected[0]
        if idx < len(self._server_ids):
            server_id = self._server_ids[idx]
            self.detail_panel.set_server(server_id)

    def _add_server(self):
        dialog = AddServerDialog(self)
        if dialog.result:
            name, host, port = dialog.result
            self.server_manager.add_server(name, host, port)
            self._refresh_server_list()

    def _remove_server(self):
        selected = self.server_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "No server selected.")
            return
        idx = selected[0]
        if idx < len(self._server_ids):
            server_id = self._server_ids[idx]
            server = self.server_manager.get_server(server_id)
            if server and messagebox.askyesno("Confirm", f"Remove server '{server.name}'?"):
                self.server_manager.remove_server(server_id)
                self.detail_panel.set_server(None)
                self._refresh_server_list()

    def _on_monitor_update(self):
        self.after(0, self._ui_update)

    def _ui_update(self):
        self._refresh_server_list()
        self.detail_panel.refresh()

    def _on_close(self):
        self.monitor_thread.stop()
        if self._agent_server:
            self._agent_server.stop()
        self.destroy()


def main():
    app = NexusCtrlApp()
    app.mainloop()


if __name__ == "__main__":
    main()