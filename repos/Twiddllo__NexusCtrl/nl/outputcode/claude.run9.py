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
from typing import Optional
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
#  Data Models
# ─────────────────────────────────────────────

class TaskPriority:
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    ALL = [CRITICAL, HIGH, MEDIUM, LOW]


class Task:
    def __init__(self, task_id: int, title: str, description: str = "",
                 priority: str = TaskPriority.MEDIUM, server_id: Optional[str] = None):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.priority = priority if priority in TaskPriority.ALL else TaskPriority.MEDIUM
        self.server_id = server_id
        self.completed = False
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None

    def complete(self):
        self.completed = True
        self.completed_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "server_id": self.server_id,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        t = cls(
            task_id=data["task_id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", TaskPriority.MEDIUM),
            server_id=data.get("server_id"),
        )
        t.completed = data.get("completed", False)
        if data.get("created_at"):
            t.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("completed_at"):
            t.completed_at = datetime.fromisoformat(data["completed_at"])
        return t


class ServerMetrics:
    def __init__(self):
        self.cpu_percent: float = 0.0
        self.ram_percent: float = 0.0
        self.ram_used_mb: float = 0.0
        self.ram_total_mb: float = 0.0
        self.net_bytes_sent: int = 0
        self.net_bytes_recv: int = 0
        self.net_send_rate: float = 0.0
        self.net_recv_rate: float = 0.0
        self.processes: list = []
        self.timestamp: datetime = datetime.now()

    def to_dict(self) -> dict:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "net_bytes_sent": self.net_bytes_sent,
            "net_bytes_recv": self.net_bytes_recv,
            "net_send_rate": self.net_send_rate,
            "net_recv_rate": self.net_recv_rate,
            "processes": self.processes,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServerMetrics":
        m = cls()
        m.cpu_percent = data.get("cpu_percent", 0.0)
        m.ram_percent = data.get("ram_percent", 0.0)
        m.ram_used_mb = data.get("ram_used_mb", 0.0)
        m.ram_total_mb = data.get("ram_total_mb", 0.0)
        m.net_bytes_sent = data.get("net_bytes_sent", 0)
        m.net_bytes_recv = data.get("net_bytes_recv", 0)
        m.net_send_rate = data.get("net_send_rate", 0.0)
        m.net_recv_rate = data.get("net_recv_rate", 0.0)
        m.processes = data.get("processes", [])
        if data.get("timestamp"):
            m.timestamp = datetime.fromisoformat(data["timestamp"])
        return m


class ServerInfo:
    def __init__(self, server_id: str, name: str, host: str, port: int = 9000):
        self.server_id = server_id
        self.name = name
        self.host = host
        self.port = port
        self.online = False
        self.last_seen: Optional[datetime] = None
        self.metrics: Optional[ServerMetrics] = None
        self.metrics_history: deque = deque(maxlen=60)
        self.last_screenshot: Optional[bytes] = None

    def update_metrics(self, metrics: ServerMetrics):
        self.metrics = metrics
        self.metrics_history.append(metrics)
        self.online = True
        self.last_seen = datetime.now()

    def mark_offline(self):
        self.online = False

    def to_dict(self) -> dict:
        return {
            "server_id": self.server_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServerInfo":
        return cls(
            server_id=data["server_id"],
            name=data["name"],
            host=data["host"],
            port=data.get("port", 9000),
        )


# ─────────────────────────────────────────────
#  Protocol helpers
# ─────────────────────────────────────────────

def send_message(sock: socket.socket, data: dict):
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)


def recv_message(sock: socket.socket) -> Optional[dict]:
    try:
        raw_len = _recv_exact(sock, 4)
        if raw_len is None:
            return None
        msg_len = struct.unpack("!I", raw_len)[0]
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
#  Agent (runs on target machine)
# ─────────────────────────────────────────────

class NexusAgent:
    """Runs as a background service on the target machine."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._prev_net = None
        self._prev_net_time = None

    def start(self):
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)
        print(f"[Agent] Listening on {self.host}:{self.port}")
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                print(f"[Agent] Connection from {addr}")
                t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"[Agent] Accept error: {e}")

    def stop(self):
        self._running = False
        if self._server_sock:
            self._server_sock.close()

    def _handle_client(self, conn: socket.socket):
        conn.settimeout(30)
        try:
            while True:
                msg = recv_message(conn)
                if msg is None:
                    break
                cmd = msg.get("cmd")
                if cmd == "get_metrics":
                    metrics = self._collect_metrics()
                    send_message(conn, {"status": "ok", "metrics": metrics.to_dict()})
                elif cmd == "get_screenshot":
                    screenshot_b64 = self._capture_screenshot()
                    send_message(conn, {"status": "ok", "screenshot": screenshot_b64})
                elif cmd == "kill_process":
                    pid = msg.get("pid")
                    result = self._kill_process(pid)
                    send_message(conn, {"status": "ok", "result": result})
                elif cmd == "ping":
                    send_message(conn, {"status": "ok", "pong": True})
                else:
                    send_message(conn, {"status": "error", "message": "Unknown command"})
        except Exception as e:
            print(f"[Agent] Client error: {e}")
        finally:
            conn.close()

    def _collect_metrics(self) -> ServerMetrics:
        m = ServerMetrics()
        if psutil is None:
            return m

        m.cpu_percent = psutil.cpu_percent(interval=0.1)

        ram = psutil.virtual_memory()
        m.ram_percent = ram.percent
        m.ram_used_mb = ram.used / (1024 * 1024)
        m.ram_total_mb = ram.total / (1024 * 1024)

        net = psutil.net_io_counters()
        now = time.time()
        if self._prev_net is not None and self._prev_net_time is not None:
            elapsed = now - self._prev_net_time
            if elapsed > 0:
                m.net_send_rate = (net.bytes_sent - self._prev_net.bytes_sent) / elapsed
                m.net_recv_rate = (net.bytes_recv - self._prev_net.bytes_recv) / elapsed
        self._prev_net = net
        self._prev_net_time = now
        m.net_bytes_sent = net.bytes_sent
        m.net_bytes_recv = net.bytes_recv

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_percent": round(info["memory_percent"] or 0.0, 2),
                    "status": info["status"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        m.processes = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:50]
        m.timestamp = datetime.now()
        return m

    def _capture_screenshot(self) -> str:
        if ImageGrab is None:
            return ""
        try:
            img = ImageGrab.grab()
            img.thumbnail((1280, 720))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[Agent] Screenshot error: {e}")
            return ""

    def _kill_process(self, pid) -> str:
        if pid is None:
            return "No PID provided"
        if psutil is None:
            return "psutil not available"
        try:
            proc = psutil.Process(int(pid))
            proc.terminate()
            return f"Process {pid} terminated"
        except psutil.NoSuchProcess:
            return f"Process {pid} not found"
        except psutil.AccessDenied:
            return f"Access denied for process {pid}"
        except Exception as e:
            return f"Error: {e}"


# ─────────────────────────────────────────────
#  Controller (connects to agents)
# ─────────────────────────────────────────────

class ServerController:
    """Manages connections to multiple agents."""

    def __init__(self, data_file: str = "nexus_data.json"):
        self.data_file = data_file
        self.servers: dict[str, ServerInfo] = {}
        self.tasks: dict[int, Task] = {}
        self._task_counter = 0
        self._monitor_threads: dict[str, threading.Thread] = {}
        self._monitor_running: dict[str, bool] = {}
        self._lock = threading.Lock()
        self._load_data()

    # ── Persistence ──────────────────────────

    def _load_data(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
            for s in data.get("servers", []):
                srv = ServerInfo.from_dict(s)
                self.servers[srv.server_id] = srv
            for t in data.get("tasks", []):
                task = Task.from_dict(t)
                self.tasks[task.task_id] = task
                if task.task_id >= self._task_counter:
                    self._task_counter = task.task_id + 1
        except Exception as e:
            print(f"[Controller] Load error: {e}")

    def save_data(self):
        try:
            data = {
                "servers": [s.to_dict() for s in self.servers.values()],
                "tasks": [t.to_dict() for t in self.tasks.values()],
            }
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Controller] Save error: {e}")

    # ── Server management ─────────────────────

    def add_server(self, name: str, host: str, port: int = 9000) -> ServerInfo:
        server_id = f"srv_{int(time.time() * 1000)}"
        srv = ServerInfo(server_id, name, host, port)
        with self._lock:
            self.servers[server_id] = srv
        self.save_data()
        return srv

    def remove_server(self, server_id: str) -> bool:
        self.stop_monitoring(server_id)
        with self._lock:
            if server_id in self.servers:
                del self.servers[server_id]
                self.save_data()
                return True
        return False

    def get_server(self, server_id: str) -> Optional[ServerInfo]:
        return self.servers.get(server_id)

    def list_servers(self) -> list:
        return list(self.servers.values())

    # ── Communication ─────────────────────────

    def _connect(self, server: ServerInfo) -> Optional[socket.socket]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((server.host, server.port))
            return sock
        except Exception:
            return None

    def ping_server(self, server_id: str) -> bool:
        srv = self.get_server(server_id)
        if srv is None:
            return False
        sock = self._connect(srv)
        if sock is None:
            srv.mark_offline()
            return False
        try:
            send_message(sock, {"cmd": "ping"})
            resp = recv_message(sock)
            if resp and resp.get("status") == "ok":
                srv.online = True
                srv.last_seen = datetime.now()
                return True
        except Exception:
            pass
        finally:
            sock.close()
        srv.mark_offline()
        return False

    def fetch_metrics(self, server_id: str) -> Optional[ServerMetrics]:
        srv = self.get_server(server_id)
        if srv is None:
            return None
        sock = self._connect(srv)
        if sock is None:
            srv.mark_offline()
            return None
        try:
            send_message(sock, {"cmd": "get_metrics"})
            resp = recv_message(sock)
            if resp and resp.get("status") == "ok":
                metrics = ServerMetrics.from_dict(resp["metrics"])
                srv.update_metrics(metrics)
                return metrics
        except Exception as e:
            print(f"[Controller] Metrics error for {server_id}: {e}")
        finally:
            sock.close()
        srv.mark_offline()
        return None

    def fetch_screenshot(self, server_id: str) -> Optional[bytes]:
        srv = self.get_server(server_id)
        if srv is None:
            return None
        sock = self._connect(srv)
        if sock is None:
            srv.mark_offline()
            return None
        try:
            send_message(sock, {"cmd": "get_screenshot"})
            resp = recv_message(sock)
            if resp and resp.get("status") == "ok":
                b64 = resp.get("screenshot", "")
                if b64:
                    data = base64.b64decode(b64)
                    srv.last_screenshot = data
                    return data
        except Exception as e:
            print(f"[Controller] Screenshot error for {server_id}: {e}")
        finally:
            sock.close()
        return None

    def kill_process(self, server_id: str, pid: int) -> str:
        srv = self.get_server(server_id)
        if srv is None:
            return "Server not found"
        sock = self._connect(srv)
        if sock is None:
            return "Cannot connect to server"
        try:
            send_message(sock, {"cmd": "kill_process", "pid": pid})
            resp = recv_message(sock)
            if resp and resp.get("status") == "ok":
                return resp.get("result", "Done")
            return "Error from agent"
        except Exception as e:
            return f"Error: {e}"
        finally:
            sock.close()

    # ── Monitoring threads ────────────────────

    def start_monitoring(self, server_id: str, interval: float = 5.0):
        if server_id in self._monitor_threads and self._monitor_threads[server_id].is_alive():
            return
        self._monitor_running[server_id] = True

        def _loop():
            while self._monitor_running.get(server_id, False):
                self.fetch_metrics(server_id)
                time.sleep(interval)

        t = threading.Thread(target=_loop, daemon=True)
        self._monitor_threads[server_id] = t
        t.start()

    def stop_monitoring(self, server_id: str):
        self._monitor_running[server_id] = False

    def start_monitoring_all(self, interval: float = 5.0):
        for sid in list(self.servers.keys()):
            self.start_monitoring(sid, interval)

    def stop_monitoring_all(self):
        for sid in list(self.servers.keys()):
            self.stop_monitoring(sid)

    # ── Task management ───────────────────────

    def create_task(self, title: str, description: str = "",
                    priority: str = TaskPriority.MEDIUM,
                    server_id: Optional[str] = None) -> Task:
        task = Task(self._task_counter, title, description, priority, server_id)
        self._task_counter += 1
        with self._lock:
            self.tasks[task.task_id] = task
        self.save_data()
        return task

    def complete_task(self, task_id: int) -> bool:
        task = self.tasks.get(task_id)
        if task is None:
            return False
        task.complete()
        self.save_data()
        return True

    def delete_task(self, task_id: int) -> bool:
        with self._lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                self.save_data()
                return True
        return False

    def list_tasks(self, server_id: Optional[str] = None,
                   completed: Optional[bool] = None) -> list:
        tasks = list(self.tasks.values())
        if server_id is not None:
            tasks = [t for t in tasks if t.server_id == server_id]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        priority_order = {TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1,
                          TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}
        tasks.sort(key=lambda t: priority_order.get(t.priority, 99))
        return tasks


# ─────────────────────────────────────────────
#  GUI (Tkinter)
# ─────────────────────────────────────────────

if HAS_TK:

    class NexusGUI:
        PRIORITY_COLORS = {
            TaskPriority.CRITICAL: "#e74c3c",
            TaskPriority.HIGH: "#e67e22",
            TaskPriority.MEDIUM: "#3498db",
            TaskPriority.LOW: "#2ecc71",
        }

        def __init__(self, controller: ServerController):
            self.controller = controller
            self.root = tk.Tk()
            self.root.title("NexusCtrl - RDP Server Management")
            self.root.geometry("1200x750")
            self.root.configure(bg="#1e1e2e")
            self._selected_server_id: Optional[str] = None
            self._build_ui()
            self._refresh_server_list()
            self._start_auto_refresh()

        # ── Build UI ──────────────────────────

        def _build_ui(self):
            self._build_menu()
            main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                                  bg="#1e1e2e", sashwidth=4)
            main.pack(fill=tk.BOTH, expand=True)

            left = tk.Frame(main, bg="#1e1e2e", width=220)
            main.add(left, minsize=180)
            self._build_server_panel(left)

            right = tk.Frame(main, bg="#1e1e2e")
            main.add(right, minsize=600)
            self._build_notebook(right)

        def _build_menu(self):
            menubar = tk.Menu(self.root)
            file_menu = tk.Menu(menubar, tearoff=0)
            file_menu.add_command(label="Add Server", command=self._dialog_add_server)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self._on_close)
            menubar.add_cascade(label="File", menu=file_menu)

            server_menu = tk.Menu(menubar, tearoff=0)
            server_menu.add_command(label="Refresh Metrics", command=self._manual_refresh)
            server_menu.add_command(label="Capture Screenshot", command=self._capture_screenshot)
            server_menu.add_separator()
            server_menu.add_command(label="Remove Server", command=self._remove_server)
            menubar.add_cascade(label="Server", menu=server_menu)

            task_menu = tk.Menu(menubar, tearoff=0)
            task_menu.add_command(label="New Task", command=self._dialog_add_task)
            menubar.add_cascade(label="Tasks", menu=task_menu)

            self.root.config(menu=menubar)

        def _build_server_panel(self, parent):
            tk.Label(parent, text="SERVERS", bg="#1e1e2e", fg="#888",
                     font=("Consolas", 9, "bold")).pack(pady=(8, 2), padx=8, anchor="w")

            btn_frame = tk.Frame(parent, bg="#1e1e2e")
            btn_frame.pack(fill=tk.X, padx=6, pady=2)
            tk.Button(btn_frame, text="+", bg="#3498db", fg="white",
                      relief=tk.FLAT, command=self._dialog_add_server,
                      font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
            tk.Button(btn_frame, text="−", bg="#e74c3c", fg="white",
                      relief=tk.FLAT, command=self._remove_server,
                      font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=4)

            frame = tk.Frame(parent, bg="#1e1e2e")
            frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.server_listbox = tk.Listbox(
                frame, bg="#2a2a3e", fg="#cdd6f4", selectbackground="#3498db",
                selectforeground="white", relief=tk.FLAT, font=("Consolas", 10),
                yscrollcommand=scrollbar.set, activestyle="none"
            )
            self.server_listbox.pack(fill=tk.BOTH, expand=True)
            scrollbar.config(command=self.server_listbox.yview)
            self.server_listbox.bind("<<ListboxSelect>>", self._on_server_select)

        def _build_notebook(self, parent):
            style = ttk.Style()
            style.theme_use("clam")
            style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
            style.configure("TNotebook.Tab", background="#2a2a3e", foreground="#cdd6f4",
                            padding=[10, 4], font=("Consolas", 10))
            style.map("TNotebook.Tab", background=[("selected", "#3498db")],
                      foreground=[("selected", "white")])

            self.notebook = ttk.Notebook(parent)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

            self._build_overview_tab()
            self._build_processes_tab()
            self._build_screenshot_tab()
            self._build_history_tab()
            self._build_tasks_tab()

        def _build_overview_tab(self):
            frame = tk.Frame(self.notebook, bg="#1e1e2e")
            self.notebook.add(frame, text="Overview")

            info_frame = tk.LabelFrame(frame, text="Server Info", bg="#1e1e2e",
                                       fg="#888", font=("Consolas", 9))
            info_frame.pack(fill=tk.X, padx=8, pady=6)

            self.lbl_server_name = self._info_label(info_frame, "Name:", "—")
            self.lbl_server_host = self._info_label(info_frame, "Host:", "—")
            self.lbl_server_status = self._info_label(info_frame, "Status:", "—")
            self.lbl_last_seen = self._info_label(info_frame, "Last Seen:", "—")

            metrics_frame = tk.LabelFrame(frame, text="Current Metrics", bg="#1e1e2e",
                                          fg="#888", font=("Consolas", 9))
            metrics_frame.pack(fill=tk.X, padx=8, pady=4)

            self.lbl_cpu = self._metric_label(metrics_frame, "CPU:")
            self.lbl_ram = self._metric_label(metrics_frame, "RAM:")
            self.lbl_net_send = self._metric_label(metrics_frame, "Net ↑:")
            self.lbl_net_recv = self._metric_label(metrics_frame, "Net ↓:")

            btn_frame = tk.Frame(frame, bg="#1e1e2e")
            btn_frame.pack(fill=tk.X, padx=8, pady=6)
            tk.Button(btn_frame, text="Refresh Metrics", bg="#3498db", fg="white",
                      relief=tk.FLAT, command=self._manual_refresh,
                      font=("Consolas", 10)).pack(side=tk.LEFT, padx=4)
            tk.Button(btn_frame, text="Capture Screenshot", bg="#9b59b6", fg="white",
                      relief=tk.FLAT, command=self._capture_screenshot,
                      font=("Consolas", 10)).pack(side=tk.LEFT, padx=4)

        def _build_processes_tab(self):
            frame = tk.Frame(self.notebook, bg="#1e1e2e")
            self.notebook.add(frame, text="Processes")

            top = tk.Frame(frame, bg="#1e1e2e")
            top.pack(fill=tk.X, padx=8, pady=4)
            tk.Button(top, text="Refresh", bg="#3498db", fg="white",
                      relief=tk.FLAT, command=self._refresh_processes,
                      font=("Consolas", 10)).pack(side=tk.LEFT)
            tk.Button(top, text="Kill Selected", bg="#e74c3c", fg="white",
                      relief=tk.FLAT, command=self._kill_selected_process,
                      font=("Consolas", 10)).pack(side=tk.LEFT, padx=6)

            cols = ("PID", "Name", "CPU%", "MEM%", "Status")
            self.proc_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                          selectmode="browse")
            style = ttk.Style()
            style.configure("Treeview", background="#2a2a3e", foreground="#cdd6f4",
                            fieldbackground="#2a2a3e", font=("Consolas", 10))
            style.configure("Treeview.Heading", background="#1e1e2e", foreground="#888",
                            font=("Consolas", 9, "bold"))
            style.map("Treeview", background=[("selected", "#3498db")])

            widths = [60, 220, 70, 70, 90]
            for col, w in zip(cols, widths):
                self.proc_tree.heading(col, text=col)
                self.proc_tree.column(col, width=w, anchor="center")

            vsb = ttk.Scrollbar(frame, orient="vertical", command=self.proc_tree.yview)
            self.proc_tree.configure(yscrollcommand=vsb.set)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            self.proc_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        def _build_screenshot_tab(self):
            frame = tk.Frame(self.notebook, bg="#1e1e2e")
            self.notebook.add(frame, text="Screenshot")

            top = tk.Frame(frame, bg="#1e1e2e")
            top.pack(fill=tk.X, padx=8, pady=4)
            tk.Button(top, text="Capture", bg="#9b59b6", fg="white",
                      relief=tk.FLAT, command=self._capture_screenshot,
                      font=("Consolas", 10)).pack(side=tk.LEFT)
            self.lbl_screenshot_time = tk.Label(top, text="", bg="#1e1e2e",
                                                fg="#888", font=("Consolas", 9))
            self.lbl_screenshot_time.pack(side=tk.LEFT, padx=10)

            self.screenshot_canvas = tk.Canvas(frame, bg="#0d0d1a", relief=tk.FLAT)
            self.screenshot_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
            self._screenshot_image = None

        def _build_history_tab(self):
            frame = tk.Frame(self.notebook, bg="#1e1e2e")
            self.notebook.add(frame, text="History")

            tk.Label(frame, text="Performance History (last 60 samples)",
                     bg="#1e1e2e", fg="#888", font=("Consolas", 9)).pack(pady=4)

            self.history_text = scrolledtext.ScrolledText(
                frame, bg="#2a2a3e", fg="#cdd6f4", font=("Consolas", 10),
                relief=tk.FLAT, state=tk.DISABLED
            )
            self.history_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        def _build_tasks_tab(self):
            frame = tk.Frame(self.notebook, bg="#1e1e2e")
            self.notebook.add(frame, text="Tasks")

            top = tk.Frame(frame, bg="#1e1e2e")
            top.pack(fill=tk.X, padx=8, pady=4)
            tk.Button(top, text="New Task", bg="#2ecc71", fg="white",
                      relief=tk.FLAT, command=self._dialog_add_task,
                      font=("Consolas", 10)).pack(side=tk.LEFT)
            tk.Button(top, text="Complete", bg="#3498db", fg="white",
                      relief=tk.FLAT, command=self._complete_task,
                      font=("Consolas", 10)).pack(side=tk.LEFT, padx=4)
            tk.Button(top, text="Delete", bg="#e74c3c", fg="white",
                      relief=tk.FLAT, command=self._delete_task,
                      font=("Consolas", 10)).pack(side=tk.LEFT)

            filter_frame = tk.Frame(frame, bg="#1e1e2e")
            filter_frame.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(filter_frame, text="Show:", bg="#1e1e2e", fg="#888",
                     font=("Consolas", 9)).pack(side=tk.LEFT)
            self.task_filter_var = tk.StringVar(value="all")
            for val, lbl in [("all", "All"), ("pending", "Pending"), ("done", "Done")]:
                tk.Radiobutton(filter_frame, text=lbl, variable=self.task_filter_var,
                               value=val, bg="#1e1e2e", fg="#cdd6f4",
                               selectcolor="#2a2a3e", activebackground="#1e1e2e",
                               command=self._refresh_tasks,
                               font=("Consolas", 9)).pack(side=tk.LEFT, padx=4)

            cols = ("ID", "Priority", "Title", "Server", "Status", "Created")
            self.task_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                          selectmode="browse")
            widths = [40, 80, 250, 120, 70, 140]
            for col, w in zip(cols, widths):
                self.task_tree.heading(col, text=col)
                self.task_tree.column(col, width=w, anchor="center")

            vsb = ttk.Scrollbar(frame, orient="vertical", command=self.task_tree.yview)
            self.task_tree.configure(yscrollcommand=vsb.set)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            self.task_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

            self._refresh_tasks()

        # ── Helpers ───────────────────────────

        def _info_label(self, parent, label: str, value: str):
            row = tk.Frame(parent, bg="#1e1e2e")
            row.pack(fill=tk.X, padx=6, pady=1)
            tk.Label(row, text=label, bg="#1e1e2e", fg="#888",
                     font=("Consolas", 9), width=10, anchor="w").pack(side=tk.LEFT)
            lbl = tk.Label(row, text=value, bg="#1e1e2e", fg="#cdd6f4",
                           font=("Consolas", 10), anchor="w")
            lbl.pack(side=tk.LEFT)
            return lbl

        def _metric_label(self, parent, label: str):
            row = tk.Frame(parent, bg="#1e1e2e")
            row.pack(fill=tk.X, padx=6, pady=2)
            tk.Label(row, text=label, bg="#1e1e2e", fg="#888",
                     font=("Consolas", 9), width=8, anchor="w").pack(side=tk.LEFT)
            lbl = tk.Label(row, text="—", bg="#1e1e2e", fg="#cdd6f4",
                           font=("Consolas", 11, "bold"), anchor="w")
            lbl.pack(side=tk.LEFT)
            return lbl

        def _fmt_bytes(self, b: float) -> str:
            if b < 1024:
                return f"{b:.0f} B/s"
            elif b < 1024 * 1024:
                return f"{b/1024:.1f} KB/s"
            else:
                return f"{b/(1024*1024):.2f} MB/s"

        # ── Server list ───────────────────────

        def _refresh_server_list(self):
            self.server_listbox.delete(0, tk.END)
            for srv in self.controller.list_servers():
                status = "●" if srv.online else "○"
                color = "#2ecc71" if srv.online else "#e74c3c"
                self.server_listbox.insert(tk.END, f"  {status}  {srv.name}")
                idx = self.server_listbox.size() - 1
                self.server_listbox.itemconfig(idx, fg=color)

        def _on_server_select(self, event):
            sel = self.server_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            servers = self.controller.list_servers()
            if idx < len(servers):
                self._selected_server_id = servers[idx].server_id
                self._update_overview()
                self._refresh_processes()
                self._refresh_history()

        def _get_selected_server(self) -> Optional[ServerInfo]:
            if self._selected_server_id is None:
                return None
            return self.controller.get_server(self._selected_server_id)

        # ── Overview ──────────────────────────

        def _update_overview(self):
            srv = self._get_selected_server()
            if srv is None:
                return
            self.lbl_server_name.config(text=srv.name)
            self.lbl_server_host.config(text=f"{srv.host}:{srv.port}")
            status_text = "ONLINE" if srv.online else "OFFLINE"
            status_color = "#2ecc71" if srv.online else "#e74c3c"
            self.lbl_server_status.config(text=status_text, fg=status_color)
            last = srv.last_seen.strftime("%H:%M:%S") if srv.last_seen else "Never"
            self.lbl_last_seen.config(text=last)

            if srv.metrics:
                m = srv.metrics
                self.lbl_cpu.config(text=f"{m.cpu_percent:.1f}%")
                self.lbl_ram.config(
                    text=f"{m.ram_percent:.1f}%  ({m.ram_used_mb:.0f}/{m.ram_total_mb:.0f} MB)"
                )
                self.lbl_net_send.config(text=self._fmt_bytes(m.net_send_rate))
                self.lbl_net_recv.config(text=self._fmt_bytes(m.net_recv_rate))
            else:
                for lbl in (self.lbl_cpu, self.lbl_ram, self.lbl_net_send, self.lbl_net_recv):
                    lbl.config(text="—")

        def _manual_refresh(self):
            srv = self._get_selected_server()
            if srv is None:
                messagebox.showinfo("Info", "Select a server first.")
                return
            threading.Thread(target=self._do_refresh, args=(srv.server_id,), daemon=True).start()

        def _do_refresh(self, server_id: str):
            self.controller.fetch_metrics(server_id)
            self.root.after(0, self._update_overview)
            self.root.after(0, self._refresh_server_list)
            self.root.after(0, self._refresh_processes)
            self.root.after(0, self._refresh_history)

        # ── Processes ─────────────────────────

        def _refresh_processes(self):
            srv = self._get_selected_server()
            for row in self.proc_tree.get_children():
                self.proc_tree.delete(row)
            if srv is None or srv.metrics is None:
                return
            for p in srv.metrics.processes:
                self.proc_tree.insert("", tk.END, values=(
                    p.get("pid", ""),
                    p.get("name", ""),
                    f"{p.get('cpu_percent', 0):.1f}",
                    f"{p.get('memory_percent', 0):.2f}",
                    p.get("status", ""),
                ))

        def _kill_selected_process(self):
            srv = self._get_selected_server()
            if srv is None:
                messagebox.showinfo("Info", "Select a server first.")
                return
            sel = self.proc_tree.selection()
            if not sel:
                messagebox.showinfo("Info", "Select a process first.")
                return
            values = self.proc_tree.item(sel[0], "values")
            pid = int(values[0])
            name = values[1]
            if not messagebox.askyesno("Confirm", f"Kill process {name} (PID {pid})?"):
                return
            result = self.controller.kill_process(srv.server_id, pid)
            messagebox.showinfo("Result", result)
            self._manual_refresh()

        # ── Screenshot ────────────────────────

        def _capture_screenshot(self):
            srv = self._get_selected_server()
            if srv is None:
                messagebox.showinfo("Info", "Select a server first.")
                return
            self.notebook.select(2)
            threading.Thread(target=self._do_screenshot, args=(srv.server_id,), daemon=True).start()

        def _do_screenshot(self, server_id: str):
            data = self.controller.fetch_screenshot(server_id)
            self.root.after(0, lambda: self._display_screenshot(data))

        def _display_screenshot(self, data: Optional[bytes]):
            if data is None or Image is None:
                self.lbl_screenshot_time.config(text="Failed to capture screenshot")
                return
            try:
                img = Image.open(io.BytesIO(data))
                canvas_w = self.screenshot_canvas.winfo_width() or 800
                canvas_h = self.screenshot_canvas.winfo_height() or 500
                img.thumbnail((canvas_w, canvas_h))
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(img)
                self.screenshot_canvas.delete("all")
                self.screenshot_canvas.create_image(
                    canvas_w // 2, canvas_h // 2, anchor="center", image=photo
                )
                self._screenshot_image = photo
                self.lbl_screenshot_time.config(
                    text=f"Captured at {datetime.now().strftime('%H:%M:%S')}"
                )
            except Exception as e:
                self.lbl_screenshot_time.config(text=f"Display error: {e}")

        # ── History ───────────────────────────

        def _refresh_history(self):
            srv = self._get_selected_server()
            self.history_text.config(state=tk.NORMAL)
            self.history_text.delete("1.0", tk.END)
            if srv is None:
                self.history_text.config(state=tk.DISABLED)
                return
            history = list(srv.metrics_history)
            if not history:
                self.history_text.insert(tk.END, "No history available.\n")
            else:
                header = f"{'Time':<12} {'CPU%':>8} {'RAM%':>8} {'Net↑':>14} {'Net↓':>14}\n"
                self.history_text.insert(tk.END, header)
                self.history_text.insert(tk.END, "─" * 60 + "\n")
                for m in reversed(history):
                    ts = m.timestamp.strftime("%H:%M:%S")
                    line = (f"{ts:<12} {m.cpu_percent:>7.1f}% {m.ram_percent:>7.1f}%"
                            f" {self._fmt_bytes(m.net_send_rate):>14}"
                            f" {self._fmt_bytes(m.net_recv_rate):>14}\n")
                    self.history_text.insert(tk.END, line)
            self.history_text.config(state=tk.DISABLED)

        # ── Tasks ─────────────────────────────

        def _refresh_tasks(self):
            for row in self.task_tree.get_children():
                self.task_tree.delete(row)
            filt = self.task_filter_var.get()
            completed_filter = None
            if filt == "pending":
                completed_filter = False
            elif filt == "done":
                completed_filter = True
            tasks = self.controller.list_tasks(completed=completed_filter)
            for t in tasks:
                srv_name = ""
                if t.server_id:
                    srv = self.controller.get_server(t.server_id)
                    srv_name = srv.name if srv else t.server_id
                status = "Done" if t.completed else "Pending"
                self.task_tree.insert("", tk.END, iid=str(t.task_id), values=(
                    t.task_id,
                    t.priority.upper(),
                    t.title,
                    srv_name,
                    status,
                    t.created_at.strftime("%Y-%m-%d %H:%M"),
                ))

        def _dialog_add_task(self):
            dlg = tk.Toplevel(self.root)
            dlg.title("New Task")
            dlg.geometry("420x320")
            dlg.configure(bg="#1e1e2e")
            dlg.grab_set()

            def lbl(text):
                tk.Label(dlg, text=text, bg="#1e1e2e", fg="#888",
                         font=("Consolas", 9)).pack(anchor="w", padx=12, pady=(6, 0))

            lbl("Title:")
            title_var = tk.StringVar()
            tk.Entry(dlg, textvariable=title_var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="white", relief=tk.FLAT,
                     font=("Consolas", 10)).pack(fill=tk.X, padx=12)

            lbl("Description:")
            desc_text = tk.Text(dlg, height=4, bg="#2a2a3e", fg="#cdd6f4",
                                insertbackground="white", relief=tk.FLAT,
                                font=("Consolas", 10))
            desc_text.pack(fill=tk.X, padx=12)

            lbl("Priority:")
            priority_var = tk.StringVar(value=TaskPriority.MEDIUM)
            pf = tk.Frame(dlg, bg="#1e1e2e")
            pf.pack(anchor="w", padx=12)
            for p in TaskPriority.ALL:
                tk.Radiobutton(pf, text=p.capitalize(), variable=priority_var,
                               value=p, bg="#1e1e2e", fg="#cdd6f4",
                               selectcolor="#2a2a3e", activebackground="#1e1e2e",
                               font=("Consolas", 9)).pack(side=tk.LEFT, padx=4)

            lbl("Server (optional):")
            server_var = tk.StringVar(value="")
            server_options = [""] + [s.name for s in self.controller.list_servers()]
            server_map = {"": None}
            for s in self.controller.list_servers():
                server_map[s.name] = s.server_id
            ttk.Combobox(dlg, textvariable=server_var, values=server_options,
                         state="readonly", font=("Consolas", 10)).pack(fill=tk.X, padx=12)

            def submit():
                title = title_var.get().strip()
                if not title:
                    messagebox.showwarning("Warning", "Title is required.", parent=dlg)
                    return
                desc = desc_text.get("1.0", tk.END).strip()
                srv_id = server_map.get(server_var.get())
                self.controller.create_task(title, desc, priority_var.get(), srv_id)
                self._refresh_tasks()
                dlg.destroy()

            tk.Button(dlg, text="Create Task", bg="#2ecc71", fg="white",
                      relief=tk.FLAT, command=submit,
                      font=("Consolas", 10)).pack(pady=10)

        def _complete_task(self):
            sel = self.task_tree.selection()
            if not sel:
                messagebox.showinfo("Info", "Select a task first.")
                return
            task_id = int(sel[0])
            self.controller.complete_task(task_id)
            self._refresh_tasks()

        def _delete_task(self):
            sel = self.task_tree.selection()
            if not sel:
                messagebox.showinfo("Info", "Select a task first.")
                return
            task_id = int(sel[0])
            if messagebox.askyesno("Confirm", f"Delete task {task_id}?"):
                self.controller.delete_task(task_id)
                self._refresh_tasks()

        # ── Server dialogs ────────────────────

        def _dialog_add_server(self):
            dlg = tk.Toplevel(self.root)
            dlg.title("Add Server")
            dlg.geometry("340x220")
            dlg.configure(bg="#1e1e2e")
            dlg.grab_set()

            def lbl(text):
                tk.Label(dlg, text=text, bg="#1e1e2e", fg="#888",
                         font=("Consolas", 9)).pack(anchor="w", padx=12, pady=(6, 0))

            lbl("Name:")
            name_var = tk.StringVar()
            tk.Entry(dlg, textvariable=name_var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="white", relief=tk.FLAT,
                     font=("Consolas", 10)).pack(fill=tk.X, padx=12)

            lbl("Host / IP:")
            host_var = tk.StringVar()
            tk.Entry(dlg, textvariable=host_var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="white", relief=tk.FLAT,
                     font=("Consolas", 10)).pack(fill=tk.X, padx=12)

            lbl("Port:")
            port_var = tk.StringVar(value="9000")
            tk.Entry(dlg, textvariable=port_var, bg="#2a2a3e", fg="#cdd6f4",
                     insertbackground="white", relief=tk.FLAT,
                     font=("Consolas", 10)).pack(fill=tk.X, padx=12)

            def submit():
                name = name_var.get().strip()
                host = host_var.get().strip()
                if not name or not host:
                    messagebox.showwarning("Warning", "Name and Host are required.", parent=dlg)
                    return
                try:
                    port = int(port_var.get())
                except ValueError:
                    messagebox.showwarning("Warning", "Invalid port.", parent=dlg)
                    return
                srv = self.controller.add_server(name, host, port)
                self.controller.start_monitoring(srv.server_id)
                self._refresh_server_list()
                dlg.destroy()

            tk.Button(dlg, text="Add Server", bg="#3498db", fg="white",
                      relief=tk.FLAT, command=submit,
                      font=("Consolas", 10)).pack(pady=10)

        def _remove_server(self):
            srv = self._get_selected_server()
            if srv is None:
                messagebox.showinfo("Info", "Select a server first.")
                return
            if messagebox.askyesno("Confirm", f"Remove server '{srv.name}'?"):
                self.controller.remove_server(srv.server_id)
                self._selected_server_id = None
                self._refresh_server_list()

        # ── Auto-refresh ──────────────────────

        def _start_auto_refresh(self):
            self.controller.start_monitoring_all(interval=10.0)
            self._schedule_ui_refresh()

        def _schedule_ui_refresh(self):
            self._refresh_server_list()
            if self._selected_server_id:
                self._update_overview()
            self.root.after(5000, self._schedule_ui_refresh)

        def _on_close(self):
            self.controller.stop_monitoring_all()
            self.controller.save_data()
            self.root.destroy()

        def run(self):
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self.root.mainloop()


# ─────────────────────────────────────────────
#  CLI fallback
# ─────────────────────────────────────────────

class NexusCLI:
    def __init__(self, controller: ServerController):
        self.controller = controller

    def run(self):
        print("NexusCtrl CLI - Type 'help' for commands")
        while True:
            try:
                line = input("nexus> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                self.controller.stop_monitoring_all()
                self.controller.save_data()
                break
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            self._dispatch(cmd, args)

    def _dispatch(self, cmd: str, args: list):
        commands = {
            "help": self._cmd_help,
            "servers": self._cmd_servers,
            "add": self._cmd_add_server,
            "remove": self._cmd_remove_server,
            "ping": self._cmd_ping,
            "metrics": self._cmd_metrics,
            "processes": self._cmd_processes,
            "kill": self._cmd_kill,
            "tasks": self._cmd_tasks,
            "task-add": self._cmd_task_add,
            "task-done": self._cmd_task_done,
            "task-del": self._cmd_task_del,
            "monitor": self._cmd_monitor,
            "exit": self._cmd_exit,
        }
        fn = commands.get(cmd)
        if fn:
            fn(args)
        else:
            print(f"Unknown command: {cmd}. Type 'help'.")

    def _cmd_help(self, args):
        print("""
Commands:
  servers                    List all servers
  add <name> <host> [port]   Add a server
  remove <server_id>         Remove a server
  ping <server_id>           Ping a server
  metrics <server_id>        Fetch metrics
  processes <server_id>      List processes
  kill <server_id> <pid>     Kill a process
  tasks [server_id]          List tasks
  task-add <title>           Add a task (interactive)
  task-done <task_id>        Mark task complete
  task-del <task_id>         Delete a task
  monitor <server_id>        Start monitoring
  exit                       Exit
""")

    def _cmd_servers(self, args):
        servers = self.controller.list_servers()
        if not servers:
            print("No servers configured.")
            return
        print(f"{'ID':<20} {'Name':<20} {'Host':<20} {'Port':<6} {'Status'}")
        print("─" * 75)
        for s in servers:
            status = "ONLINE" if s.online else "OFFLINE"
            print(f"{s.server_id:<20} {s.name:<20} {s.host:<20} {s.port:<6} {status}")

    def _cmd_add_server(self, args):
        if len(args) < 2:
            print("Usage: add <name> <host> [port]")
            return
        name, host = args[0], args[1]
        port = int(args[2]) if len(args) > 2 else 9000
        srv = self.controller.add_server(name, host, port)
        print(f"Added server: {srv.server_id}")

    def _cmd_remove_server(self, args):
        if not args:
            print("Usage: remove <server_id>")
            return
        if self.controller.remove_server(args[0]):
            print("Server removed.")
        else:
            print("Server not found.")

    def _cmd_ping(self, args):
        if not args:
            print("Usage: ping <server_id>")
            return
        result = self.controller.ping_server(args[0])
        print("ONLINE" if result else "OFFLINE")

    def _cmd_metrics(self, args):
        if not args:
            print("Usage: metrics <server_id>")
            return
        m = self.controller.fetch_metrics(args[0])
        if m is None:
            print("Failed to fetch metrics.")
            return
        print(f"CPU:     {m.cpu_percent:.1f}%")
        print(f"RAM:     {m.ram_percent:.1f}%  ({m.ram_used_mb:.0f}/{m.ram_total_mb:.0f} MB)")
        print(f"Net ↑:   {m.net_send_rate/1024:.1f} KB/s")
        print(f"Net ↓:   {m.net_recv_rate/1024:.1f} KB/s")

    def _cmd_processes(self, args):
        if not args:
            print("Usage: processes <server_id>")
            return
        m = self.controller.fetch_metrics(args[0])
        if m is None:
            print("Failed to fetch metrics.")
            return
        print(f"{'PID':<8} {'Name':<30} {'CPU%':>6} {'MEM%':>6} {'Status'}")
        print("─" * 65)
        for p in m.processes[:20]:
            print(f"{p['pid']:<8} {p['name']:<30} {p['cpu_percent']:>5.1f}%"
                  f" {p['memory_percent']:>5.2f}% {p['status']}")

    def _cmd_kill(self, args):
        if len(args) < 2:
            print("Usage: kill <server_id> <pid>")
            return
        result = self.controller.kill_process(args[0], int(args[1]))
        print(result)

    def _cmd_tasks(self, args):
        server_id = args[0] if args else None
        tasks = self.controller.list_tasks(server_id=server_id)
        if not tasks:
            print("No tasks.")
            return
        print(f"{'ID':<5} {'Priority':<10} {'Title':<30} {'Status'}")
        print("─" * 60)
        for t in tasks:
            status = "Done" if t.completed else "Pending"
            print(f"{t.task_id:<5} {t.priority:<10} {t.title:<30} {status}")

    def _cmd_task_add(self, args):
        title = " ".join(args) if args else input("Title: ").strip()
        desc = input("Description (optional): ").strip()
        print(f"Priority [{'/'.join(TaskPriority.ALL)}]: ", end="")
        priority = input().strip().lower()
        if priority not in TaskPriority.ALL:
            priority = TaskPriority.MEDIUM
        task = self.controller.create_task(title, desc, priority)
        print(f"Task created: #{task.task_id}")

    def _cmd_task_done(self, args):
        if not args:
            print("Usage: task-done <task_id>")
            return
        if self.controller.complete_task(int(args[0])):
            print("Task marked complete.")
        else:
            print("Task not found.")

    def _cmd_task_del(self, args):
        if not args:
            print("Usage: task-del <task_id>")
            return
        if self.controller.delete_task(int(args[0])):
            print("Task deleted.")
        else:
            print("Task not found.")

    def _cmd_monitor(self, args):
        if not args:
            print("Usage: monitor <server_id>")
            return
        self.controller.start_monitoring(args[0])
        print(f"Monitoring started for {args[0]}")

    def _cmd_exit(self, args):
        self.controller.stop_monitoring_all()
        self.controller.save_data()
        sys.exit(0)


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NexusCtrl - RDP Server Management")
    parser.add_argument("--agent", action="store_true", help="Run as agent on this machine")
    parser.add_argument("--agent-host", default="0.0.0.0", help="Agent bind host")
    parser.add_argument("--agent-port", type=int, default=9000, help="Agent bind port")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode")
    parser.add_argument("--data", default="nexus_data.json", help="Data file path")
    args = parser.parse_args()

    if args.agent:
        agent = NexusAgent(host=args.agent_host, port=args.agent_port)
        try:
            agent.start()
        except KeyboardInterrupt:
            print("\n[Agent] Stopping.")
            agent.stop()
        return

    controller = ServerController(data_file=args.data)

    if not args.cli and HAS_TK:
        try:
            gui = NexusGUI(controller)
            gui.run()
        except Exception as e:
            print(f"GUI error: {e}. Falling back to CLI.")
            cli = NexusCLI(controller)
            cli.run()
    else:
        cli = NexusCLI(controller)
        cli.run()


if __name__ == "__main__":
    main()