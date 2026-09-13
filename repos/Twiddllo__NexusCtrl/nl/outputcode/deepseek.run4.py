import json
import socket
import threading
import time
import sys
import traceback
import base64
import io
import queue
import uuid
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

DEFAULT_AGENT_PORT = 9999
BUFFER_SIZE = 4096
MAX_HISTORY_POINTS = 100


class Priority(Enum):
    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class TaskStatus(Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.lock = threading.Lock()

    def add_task(self, name: str, description: str = "", priority: Priority = Priority.MEDIUM) -> Task:
        with self.lock:
            task = Task(name=name, description=description, priority=priority)
            self.tasks[task.id] = task
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self.lock:
            return self.tasks.get(task_id)

    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        with self.lock:
            if status_filter:
                return [t for t in self.tasks.values() if t.status == status_filter]
            return list(self.tasks.values())

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> bool:
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = new_status
                task.updated_at = datetime.utcnow()
                return True
            return False

    def delete_task(self, task_id: str) -> bool:
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False


@dataclass
class ServerMetrics:
    cpu_percent: float = 0.0
    ram_total: int = 0
    ram_used: int = 0
    ram_free: int = 0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            'cpu_percent': self.cpu_percent,
            'ram_total': self.ram_total,
            'ram_used': self.ram_used,
            'ram_free': self.ram_free,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_recv': self.network_bytes_recv,
            'timestamp': self.timestamp
        }


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0

    def to_dict(self):
        return {
            'pid': self.pid,
            'name': self.name,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent
        }


class ServerConnection:
    def __init__(self, host: str, port: int = DEFAULT_AGENT_PORT, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.lock = threading.Lock()

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            return True
        except (socket.error, OSError):
            self.sock = None
            return False

    def disconnect(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None

    def send_command(self, command: str, data: Optional[Dict] = None) -> Optional[Dict]:
        if not self.sock:
            return None
        msg = json.dumps({"command": command, "data": data or {}}).encode('utf-8')
        try:
            with self.lock:
                self.sock.sendall(msg + b'\n')
                response_data = b''
                while True:
                    chunk = self.sock.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    response_data += chunk
                    if b'\n' in response_data:
                        break
                if response_data:
                    response = json.loads(response_data.strip().decode('utf-8'))
                    return response
        except (socket.timeout, ConnectionError, json.JSONDecodeError, OSError):
            self.disconnect()
        return None

    def send_raw(self, data: bytes) -> bool:
        if not self.sock:
            return False
        try:
            self.sock.sendall(data)
            return True
        except:
            self.disconnect()
            return False

    def recv_raw(self, size: int) -> Optional[bytes]:
        if not self.sock:
            return None
        try:
            data = b''
            while len(data) < size:
                chunk = self.sock.recv(min(size - len(data), BUFFER_SIZE))
                if not chunk:
                    return None
                data += chunk
            return data
        except (socket.timeout, ConnectionError, OSError):
            self.disconnect()
            return None


class ServerManager:
    def __init__(self):
        self.servers: Dict[str, ServerConnection] = {}
        self.server_names: Dict[str, str] = {}  # address -> friendly name
        self.metrics_cache: Dict[str, ServerMetrics] = {}
        self.processes_cache: Dict[str, List[ProcessInfo]] = {}
        self.history: Dict[str, List[ServerMetrics]] = {}
        self.lock = threading.Lock()
        self.running = False
        self.monitor_thread = None

    def add_server(self, name: str, host: str, port: int = DEFAULT_AGENT_PORT):
        with self.lock:
            key = f"{host}:{port}"
            self.server_names[key] = name
            if key not in self.servers:
                self.servers[key] = ServerConnection(host, port)
                self.history[key] = []

    def remove_server(self, host: str, port: int):
        key = f"{host}:{port}"
        with self.lock:
            if key in self.servers:
                self.servers[key].disconnect()
                del self.servers[key]
                del self.server_names[key]
                self.history.pop(key, None)
                self.metrics_cache.pop(key, None)
                self.processes_cache.pop(key, None)

    def get_status(self, key: str) -> bool:
        with self.lock:
            conn = self.servers.get(key)
            if not conn:
                return False
        resp = conn.send_command("status")
        if resp and resp.get("status") == "ok":
            return True
        return False

    def fetch_metrics(self, key: str) -> Optional[ServerMetrics]:
        conn = self.servers.get(key)
        if not conn:
            return None
        resp = conn.send_command("metrics")
        if not resp or resp.get("status") != "ok":
            return None
        data = resp.get("data", {})
        metrics = ServerMetrics(
            cpu_percent=data.get("cpu_percent", 0.0),
            ram_total=data.get("ram_total", 0),
            ram_used=data.get("ram_used", 0),
            ram_free=data.get("ram_free", 0),
            network_bytes_sent=data.get("network_bytes_sent", 0),
            network_bytes_recv=data.get("network_bytes_recv", 0),
            timestamp=data.get("timestamp", time.time())
        )
        with self.lock:
            self.metrics_cache[key] = metrics
            history = self.history.setdefault(key, [])
            history.append(metrics)
            if len(history) > MAX_HISTORY_POINTS:
                history.pop(0)
        return metrics

    def fetch_processes(self, key: str) -> Optional[List[ProcessInfo]]:
        conn = self.servers.get(key)
        if not conn:
            return None
        resp = conn.send_command("processes")
        if not resp or resp.get("status") != "ok":
            return None
        processes = []
        for p in resp.get("data", []):
            processes.append(ProcessInfo(**p))
        with self.lock:
            self.processes_cache[key] = processes
        return processes

    def kill_process(self, key: str, pid: int) -> bool:
        conn = self.servers.get(key)
        if not conn:
            return False
        resp = conn.send_command("kill", {"pid": pid})
        return resp is not None and resp.get("status") == "ok"

    def capture_screen(self, key: str) -> Optional[bytes]:
        conn = self.servers.get(key)
        if not conn:
            return None
        resp = conn.send_command("screen_prepare")
        if not resp or resp.get("status") != "ok":
            return None
        # Agent will respond with image size
        img_size = resp.get("data", {}).get("size")
        if not img_size:
            return None
        # Now receive binary stream
        conn.send_raw(b'READY\n')
        # Read expected size from header maybe. Instead agent sends size then data.
        # We'll implement: agent sends size as 8 bytes (big-endian), then data.
        size_bytes = conn.recv_raw(8)
        if not size_bytes:
            return None
        total = int.from_bytes(size_bytes, 'big')
        image_data = conn.recv_raw(total)
        return image_data

    def start_monitoring(self, interval=5):
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

    def _monitoring_loop(self, interval):
        while self.running:
            with self.lock:
                keys = list(self.servers.keys())
            for key in keys:
                conn = self.servers.get(key)
                if not conn:
                    continue
                # Try to fetch metrics
                self.fetch_metrics(key)
            time.sleep(interval)


class NexusAgent:
    def __init__(self, host='0.0.0.0', port=DEFAULT_AGENT_PORT):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False

    def start(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        print(f"Agent listening on {self.host}:{self.port}")
        while self.running:
            try:
                client, addr = self.socket.accept()
                print(f"Connection from {addr}")
                client.settimeout(30)
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
            except Exception as e:
                if self.running:
                    traceback.print_exc()

    def stop(self):
        self.running = False
        try:
            self.socket.close()
        except:
            pass

    def handle_client(self, client: socket.socket):
        try:
            with client:
                buffer = b''
                while True:
                    data = client.recv(BUFFER_SIZE)
                    if not data:
                        break
                    buffer += data
                    if b'\n' in buffer:
                        command_data, buffer = buffer.split(b'\n', 1)
                        try:
                            msg = json.loads(command_data.decode('utf-8'))
                            response = self.process_command(msg, client)
                            client.sendall(json.dumps(response).encode('utf-8') + b'\n')
                        except json.JSONDecodeError:
                            client.sendall(json.dumps({"status": "error", "message": "invalid json"}).encode('utf-8') + b'\n')
        except Exception as e:
            traceback.print_exc()
        finally:
            try:
                client.close()
            except:
                pass

    def process_command(self, msg: dict, client: socket.socket) -> dict:
        command = msg.get("command")
        data = msg.get("data", {})
        if command == "status":
            return {"status": "ok", "data": {"agent": "NexusAgent", "time": time.time()}}
        elif command == "metrics":
            return self.get_metrics()
        elif command == "processes":
            return self.get_processes()
        elif command == "kill":
            pid = data.get("pid")
            if pid is None:
                return {"status": "error", "message": "pid required"}
            success = self.kill_process(pid)
            return {"status": "ok" if success else "error", "message": "" if success else "failed to kill"}
        elif command == "screen_prepare":
            return self.prepare_screen_capture()
        else:
            return {"status": "error", "message": f"unknown command {command}"}

    def get_metrics(self) -> dict:
        if not HAS_PSUTIL:
            return {"status": "error", "message": "psutil not installed"}
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        net = psutil.net_io_counters()
        return {
            "status": "ok",
            "data": {
                "cpu_percent": cpu,
                "ram_total": mem.total,
                "ram_used": mem.used,
                "ram_free": mem.free,
                "network_bytes_sent": net.bytes_sent,
                "network_bytes_recv": net.bytes_recv,
                "timestamp": time.time()
            }
        }

    def get_processes(self) -> dict:
        if not HAS_PSUTIL:
            return {"status": "error", "message": "psutil not installed"}
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                procs.append({
                    "pid": p.info['pid'],
                    "name": p.info['name'],
                    "cpu_percent": p.info['cpu_percent'] or 0.0,
                    "memory_percent": p.info['memory_percent'] or 0.0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {"status": "ok", "data": procs}

    def kill_process(self, pid: int) -> bool:
        if not HAS_PSUTIL:
            return False
        try:
            p = psutil.Process(pid)
            p.terminate()
            return True
        except:
            return False

    def prepare_screen_capture(self) -> dict:
        if not HAS_PIL:
            return {"status": "error", "message": "PIL not installed"}
        # Capture screen into memory
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_bytes = buf.getvalue()
        return {"status": "ok", "data": {"size": len(img_bytes), "format": "png"}}

    def handle_screen_transfer(self, client: socket.socket, img_bytes: bytes):
        # After sending the prepare response, the controller sends READY, then we send size and data
        # But in our protocol, the controller sends a separate raw message after receiving prepare response.
        # So after process_command returns, the caller sends the response. Then we need to wait for READY.
        # We'll implement this by handling screen capture as a special command that doesn't send the image immediately,
        # but after receiving READY. Let's refactor: In handle_client loop, after sending response for screen_prepare,
        # we wait for exactly "READY\n" then send the image.
        pass


# The agent needs to handle screen capture specially because it involves binary data.
# We'll modify NexusAgent to have a more elaborate protocol in handle_client for the screen capture command.
# Simpler: We'll define a "capture" command that directly sends base64 encoded image in JSON (inefficient but works).
# Since spec mentions live screen capture, maybe large image, but for demo base64 is fine.
# Let's change agent to use base64 encoding for screen.
class NexusAgentV2(NexusAgent):
    def process_command(self, msg: dict, client: socket.socket) -> dict:
        command = msg.get("command")
        if command == "capture":
            return self.capture_screen_base64()
        return super().process_command(msg, client)

    def capture_screen_base64(self) -> dict:
        if not HAS_PIL:
            return {"status": "error", "message": "PIL not installed"}
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        return {"status": "ok", "data": {"image": b64_str, "format": "png"}}


# We'll use V2 agent by default
NexusAgent = NexusAgentV2


class NexusCtrl:
    def __init__(self):
        self.server_manager = ServerManager()
        self.task_manager = TaskManager()
        self.running = False
        self.monitoring_interval = 5

    def start_cli(self):
        print("NexusCtrl - Personal RDP Server Management Tool")
        print("Type 'help' for available commands.")
        self.server_manager.start_monitoring(self.monitoring_interval)
        self.running = True
        while self.running:
            try:
                cmd_line = input("> ").strip()
                if not cmd_line:
                    continue
                self.execute_command(cmd_line)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
        self.server_manager.stop_monitoring()

    def execute_command(self, cmd_line: str):
        parts = cmd_line.split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "help":
            self.show_help()
        elif cmd == "servers":
            self.list_servers()
        elif cmd == "add":
            self.add_server(args)
        elif cmd == "remove":
            self.remove_server(args)
        elif cmd == "monitor":
            self.monitor_server(args)
        elif cmd == "processes":
            self.show_processes(args)
        elif cmd == "kill":
            self.kill_process(args)
        elif cmd == "capture":
            self.capture_screen(args)
        elif cmd == "history":
            self.show_history(args)
        elif cmd == "task":
            self.handle_task(args)
        elif cmd == "quit" or cmd == "exit":
            self.running = False
        else:
            print("Unknown command. Type 'help'.")

    def show_help(self):
        help_text = """
Available commands:
  servers                 - List all configured servers and their status
  add <name> <host> [port]- Add a new server (default port 9999)
  remove <host> [port]    - Remove a server
  monitor <host> [port]   - Display live metrics for a server (press Ctrl+C to stop)
  processes <host> [port] - List processes on a server
  kill <host> <pid>       - Terminate a process on a server
  capture <host> [port]   - Capture screen from a server (saves as capture_<host>.png)
  history <host> [port]   - Show performance history for a server
  task list [status]      - List tasks (optionally filter by status: pending/in_progress/completed)
  task add <name> [desc] [priority]  - Add a new task (priority: critical/high/medium/low)
  task update <id> <status>          - Update task status
  task delete <id>        - Delete a task
  quit/exit               - Exit NexusCtrl
"""
        print(help_text)

    def _resolve_server_key(self, args: list) -> Optional[str]:
        if not args:
            print("Server host required.")
            return None
        host = args[0]
        port = int(args[1]) if len(args) > 1 else DEFAULT_AGENT_PORT
        key = f"{host}:{port}"
        if key not in self.server_manager.servers:
            print(f"Server {key} not found.")
            return None
        return key

    def list_servers(self):
        with self.server_manager.lock:
            if not self.server_manager.servers:
                print("No servers configured.")
                return
            print(f"{'Name':<15} {'Host':<15} {'Port':<7} {'Status'}")
            print("-"*50)
            for key, conn in self.server_manager.servers.items():
                host, port_str = key.split(':')
                port = int(port_str)
                name = self.server_manager.server_names.get(key, host)
                online = self.server_manager.get_status(key)
                status = "online" if online else "offline"
                print(f"{name:<15} {host:<15} {port:<7} {status}")

    def add_server(self, args: list):
        if not args:
            print("Usage: add <name> <host> [port]")
            return
        name = args[0]
        host = args[1] if len(args) > 1 else None
        if not host:
            print("Host required.")
            return
        port = int(args[2]) if len(args) > 2 else DEFAULT_AGENT_PORT
        self.server_manager.add_server(name, host, port)
        print(f"Added server {name} ({host}:{port})")

    def remove_server(self, args: list):
        if not args:
            print("Usage: remove <host> [port]")
            return
        host = args[0]
        port = int(args[1]) if len(args) > 1 else DEFAULT_AGENT_PORT
        self.server_manager.remove_server(host, port)
        print(f"Removed server {host}:{port}")

    def monitor_server(self, args: list):
        key = self._resolve_server_key(args)
        if not key:
            return
        print(f"Monitoring {key}. Press Ctrl+C to stop.")
        try:
            while True:
                metrics = self.server_manager.fetch_metrics(key)
                processes = self.server_manager.fetch_processes(key)
                if metrics:
                    print(f"\n--- {datetime.now().strftime('%H:%M:%S')} ---")
                    print(f"CPU: {metrics.cpu_percent:.1f}%")
                    print(f"RAM: {metrics.ram_used//(1024**2)}/{metrics.ram_total//(1024**2)} MB (Free: {metrics.ram_free//(1024**2)} MB)")
                    net_sent = metrics.network_bytes_sent / (1024**2)
                    net_recv = metrics.network_bytes_recv / (1024**2)
                    print(f"Network: Sent {net_sent:.2f} MB, Recv {net_recv:.2f} MB")
                    if processes:
                        print(f"Processes: {len(processes)} running")
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nStopped monitoring.")

    def show_processes(self, args: list):
        key = self._resolve_server_key(args)
        if not key:
            return
        processes = self.server_manager.fetch_processes(key)
        if processes is None:
            print("Failed to retrieve process list.")
            return
        print(f"{'PID':<8} {'Name':<25} {'CPU%':<8} {'MEM%'}")
        print("-"*50)
        for p in sorted(processes, key=lambda x: x.cpu_percent, reverse=True)[:30]:
            print(f"{p.pid:<8} {p.name:<25} {p.cpu_percent:<8.1f} {p.memory_percent:.1f}")

    def kill_process(self, args: list):
        if len(args) < 2:
            print("Usage: kill <host> <pid>")
            return
        host = args[0]
        port = DEFAULT_AGENT_PORT
        if len(args) > 2:
            port = int(args[1])
            pid = int(args[2])
        else:
            pid = int(args[1])
        key = f"{host}:{port}"
        if key not in self.server_manager.servers:
            print(f"Server {key} not found.")
            return
        success = self.server_manager.kill_process(key, pid)
        if success:
            print(f"Process {pid} terminated.")
        else:
            print("Failed to kill process.")

    def capture_screen(self, args: list):
        key = self._resolve_server_key(args)
        if not key:
            return
        conn = self.server_manager.servers.get(key)
        if not conn:
            print("Server not found.")
            return
        # Use base64 capture command
        resp = conn.send_command("capture")
        if not resp or resp.get("status") != "ok":
            print("Screen capture failed.")
            return
        img_b64 = resp.get("data", {}).get("image")
        if not img_b64:
            print("No image data.")
            return
        img_bytes = base64.b64decode(img_b64)
        filename = f"capture_{key.replace(':', '_')}.png"
        with open(filename, 'wb') as f:
            f.write(img_bytes)
        print(f"Screen capture saved to {filename}")

    def show_history(self, args: list):
        key = self._resolve_server_key(args)
        if not key:
            return
        history = self.server_manager.history.get(key, [])
        if not history:
            print("No history available.")
            return
        print(f"History for {key} (last {len(history)} points):")
        print(f"{'Time':<20} {'CPU%':<8} {'RAM Used(MB)':<15}")
        print("-"*45)
        for m in history[-20:]:
            ts = datetime.fromtimestamp(m.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            ram_mb = m.ram_used // (1024**2)
            print(f"{ts:<20} {m.cpu_percent:<8.1f} {ram_mb:<15}")

    def handle_task(self, args: list):
        if not args:
            print("Usage: task <list|add|update|delete> ...")
            return
        subcmd = args[0].lower()
        if subcmd == "list":
            status_filter = None
            if len(args) > 1:
                try:
                    status_filter = TaskStatus(args[1])
                except ValueError:
                    print("Invalid status. Use pending/in_progress/completed")
                    return
            tasks = self.task_manager.list_tasks(status_filter)
            if not tasks:
                print("No tasks found.")
                return
            print(f"{'ID':<36} {'Name':<15} {'Priority':<10} {'Status':<12} {'Created'}")
            print("-"*90)
            for t in tasks:
                print(f"{t.id:<36} {t.name:<15} {t.priority.value:<10} {t.status.value:<12} {t.created_at.strftime('%Y-%m-%d %H:%M')}")
        elif subcmd == "add":
            if len(args) < 2:
                print("Usage: task add <name> [description] [priority]")
                return
            name = args[1]
            desc = args[2] if len(args) > 2 else ""
            priority_str = args[3] if len(args) > 3 else "medium"
            try:
                priority = Priority(priority_str)
            except ValueError:
                print("Invalid priority. Options: critical, high, medium, low")
                return
            task = self.task_manager.add_task(name, desc, priority)
            print(f"Task added with ID: {task.id}")
        elif subcmd == "update":
            if len(args) < 3:
                print("Usage: task update <id> <status>")
                return
            task_id = args[1]
            status_str = args[2]
            try:
                new_status = TaskStatus(status_str)
            except ValueError:
                print("Invalid status. Use pending/in_progress/completed")
                return
            success = self.task_manager.update_task_status(task_id, new_status)
            if success:
                print("Task updated.")
            else:
                print("Task not found.")
        elif subcmd == "delete":
            if len(args) < 2:
                print("Usage: task delete <id>")
                return
            task_id = args[1]
            if self.task_manager.delete_task(task_id):
                print("Task deleted.")
            else:
                print("Task not found.")
        else:
            print("Unknown task subcommand.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--agent':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_AGENT_PORT
        agent = NexusAgent(port=port)
        try:
            agent.start()
        except KeyboardInterrupt:
            print("Agent shutting down.")
            agent.stop()
    else:
        ctrl = NexusCtrl()
        ctrl.start_cli()


if __name__ == '__main__':
    main()