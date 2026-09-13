import argparse
import base64
import io
import json
import os
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from queue import Queue
from typing import Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None
    print("psutil is required for agent functionality. Install with: pip install psutil")
    sys.exit(1)

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None
    print("Pillow is required for screen capture. Install with: pip install Pillow")
    sys.exit(1)


# --------------------- Enums --------------------- #
class TaskStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


# --------------------- Data Classes --------------------- #
@dataclass
class Task:
    task_id: int
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_status(self, new_status: TaskStatus):
        self.status = new_status
        self.updated_at = datetime.now()


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float


@dataclass
class MetricSnapshot:
    timestamp: datetime
    cpu_percent: float
    memory_total: int
    memory_available: int
    memory_percent: float
    network_bytes_sent: int
    network_bytes_recv: int


# --------------------- Task Manager --------------------- #
class TaskManager:
    def __init__(self):
        self._tasks: Dict[int, Task] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def create_task(self, description: str, priority_str: str) -> Task:
        try:
            priority = TaskPriority[priority_str.upper()]
        except KeyError:
            raise ValueError(f"Invalid priority: {priority_str}. Use critical, high, medium, low.")

        with self._lock:
            task = Task(task_id=self._next_id, description=description, priority=priority)
            self._tasks[self._next_id] = task
            self._next_id += 1
            return task

    def get_task(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_task_status(self, task_id: int, new_status_str: str) -> bool:
        try:
            new_status = TaskStatus[new_status_str.upper().replace("-", "_")]
        except KeyError:
            raise ValueError(f"Invalid status: {new_status_str}. Use pending, in-progress, completed.")

        task = self._tasks.get(task_id)
        if task:
            task.update_status(new_status)
            return True
        return False

    def list_tasks(self, priority_filter: Optional[str] = None, status_filter: Optional[str] = None) -> List[Task]:
        tasks = list(self._tasks.values())
        if priority_filter:
            try:
                prio = TaskPriority[priority_filter.upper()]
                tasks = [t for t in tasks if t.priority == prio]
            except KeyError:
                pass
        if status_filter:
            try:
                stat = TaskStatus[status_filter.upper().replace("-", "_")]
                tasks = [t for t in tasks if t.status == stat]
            except KeyError:
                pass
        return tasks

    def delete_task(self, task_id: int) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
        return False


# --------------------- Server Monitor --------------------- #
class ServerMonitor:
    def __init__(self, agent_host: str, agent_port: int, agent_id: str, poll_interval: float = 5.0):
        self.agent_host = agent_host
        self.agent_port = agent_port
        self.agent_id = agent_id
        self.poll_interval = poll_interval
        self._online = False
        self._stop_event = threading.Event()
        self._history: List[MetricSnapshot] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._last_processes: List[ProcessInfo] = []

    @property
    def status(self) -> ServerStatus:
        return ServerStatus.ONLINE if self._online else ServerStatus.OFFLINE

    def _send_command(self, command: str, timeout: float = 3.0) -> Optional[dict]:
        """Send a JSON command to the agent and return parsed response."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((self.agent_host, self.agent_port))
                message = json.dumps({"command": command}).encode()
                # Prefix with message length (4 bytes, big-endian)
                sock.sendall(struct.pack('>I', len(message)) + message)

                # Read response length
                raw_len = self._recv_all(sock, 4)
                if not raw_len:
                    return None
                resp_len = struct.unpack('>I', raw_len)[0]
                resp_data = self._recv_all(sock, resp_len)
                if resp_data is None:
                    return None
                return json.loads(resp_data.decode())
        except (socket.timeout, ConnectionRefusedError, OSError):
            return None

    def _recv_all(self, sock: socket.socket, n: int) -> Optional[bytes]:
        data = bytearray()
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
            except socket.timeout:
                return None
            if not packet:
                return None
            data.extend(packet)
        return data

    def _check_online(self) -> bool:
        """Quick health check: send ping command."""
        resp = self._send_command("ping", timeout=1.0)
        return resp is not None and resp.get("status") == "ok"

    def _fetch_metrics(self) -> Optional[MetricSnapshot]:
        resp = self._send_command("get_metrics")
        if resp and resp.get("status") == "ok":
            data = resp["data"]
            return MetricSnapshot(
                timestamp=datetime.fromisoformat(data["timestamp"]),
                cpu_percent=data["cpu_percent"],
                memory_total=data["memory_total"],
                memory_available=data["memory_available"],
                memory_percent=data["memory_percent"],
                network_bytes_sent=data["network_bytes_sent"],
                network_bytes_recv=data["network_bytes_recv"],
            )
        return None

    def get_processes(self) -> List[ProcessInfo]:
        resp = self._send_command("get_processes")
        if resp and resp.get("status") == "ok":
            self._last_processes = [ProcessInfo(**p) for p in resp["processes"]]
            return self._last_processes
        return []

    def kill_process(self, pid: int) -> bool:
        resp = self._send_command(f"kill_process {pid}")
        return resp is not None and resp.get("status") == "ok"

    def get_screen_capture(self) -> Optional[bytes]:
        """Returns raw PNG bytes of screen capture."""
        resp = self._send_command("screen_capture")
        if resp and resp.get("status") == "ok":
            return base64.b64decode(resp["image_base64"])
        return None

    def get_history(self) -> List[MetricSnapshot]:
        with self._lock:
            return list(self._history)

    def _poll_loop(self):
        while not self._stop_event.is_set():
            if self._check_online():
                self._online = True
                snapshot = self._fetch_metrics()
                if snapshot:
                    with self._lock:
                        self._history.append(snapshot)
                        # Keep last 1000 entries
                        if len(self._history) > 1000:
                            self._history = self._history[-1000:]
                # Also fetch processes for local cache (optional)
                self.get_processes()
            else:
                self._online = False
            self._stop_event.wait(self.poll_interval)

    def start_monitoring(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)


# --------------------- Agent Server --------------------- #
class AgentServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        self.host = host
        self.port = port
        self._server_socket: Optional[socket.socket] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _get_metrics(self) -> dict:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        net = psutil.net_io_counters()
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu,
            "memory_total": mem.total,
            "memory_available": mem.available,
            "memory_percent": mem.percent,
            "network_bytes_sent": net.bytes_sent,
            "network_bytes_recv": net.bytes_recv,
        }

    def _get_processes(self) -> List[dict]:
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                procs.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent'],
                    "memory_percent": info['memory_percent'],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return procs

    def _kill_process(self, pid: int) -> bool:
        try:
            process = psutil.Process(pid)
            process.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _capture_screen(self) -> bytes:
        if ImageGrab is None:
            raise RuntimeError("Pillow not installed")
        img = ImageGrab.grab()
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _handle_client(self, conn: socket.socket, addr: tuple):
        try:
            # Receive message length
            raw_len = self._recv_all(conn, 4)
            if not raw_len:
                return
            msg_len = struct.unpack('>I', raw_len)[0]
            msg_data = self._recv_all(conn, msg_len)
            if not msg_data:
                return
            cmd_obj = json.loads(msg_data.decode())
            command = cmd_obj.get("command", "")
            response = {}

            if command == "ping":
                response = {"status": "ok"}
            elif command == "get_metrics":
                response = {"status": "ok", "data": self._get_metrics()}
            elif command == "get_processes":
                response = {"status": "ok", "processes": self._get_processes()}
            elif command.startswith("kill_process"):
                parts = command.split()
                if len(parts) == 2 and parts[1].isdigit():
                    pid = int(parts[1])
                    success = self._kill_process(pid)
                    response = {"status": "ok" if success else "error", "message": f"Kill {'successful' if success else 'failed'}"}
                else:
                    response = {"status": "error", "message": "Invalid PID"}
            elif command == "screen_capture":
                try:
                    img_bytes = self._capture_screen()
                    response = {"status": "ok", "image_base64": base64.b64encode(img_bytes).decode()}
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
            else:
                response = {"status": "error", "message": "Unknown command"}

            resp_bytes = json.dumps(response).encode()
            conn.sendall(struct.pack('>I', len(resp_bytes)) + resp_bytes)
        except Exception:
            pass
        finally:
            conn.close()

    def _recv_all(self, sock: socket.socket, n: int) -> Optional[bytes]:
        data = bytearray()
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
            except (socket.timeout, ConnectionResetError):
                return None
            if not packet:
                return None
            data.extend(packet)
        return data

    def _run_server(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)
        print(f"Agent listening on {self.host}:{self.port}")

        while not self._stop_event.is_set():
            try:
                conn, addr = self._server_socket.accept()
                client_thread = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                client_thread.start()
            except socket.timeout:
                continue
            except OSError:
                break

        if self._server_socket:
            self._server_socket.close()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._server_socket:
            try:
                # Connect to unblock accept
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('127.0.0.1', self.port))
                sock.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)


# --------------------- NexusCtrl Controller --------------------- #
class NexusCtrl:
    def __init__(self):
        self.servers: Dict[str, ServerMonitor] = {}
        self.task_manager = TaskManager()
        self.running = True

    def add_server(self, server_id: str, host: str, port: int = 9000):
        if server_id in self.servers:
            print(f"Server '{server_id}' already exists.")
            return
        monitor = ServerMonitor(host, port, server_id)
        self.servers[server_id] = monitor
        print(f"Added server '{server_id}' at {host}:{port}")

    def remove_server(self, server_id: str):
        if server_id in self.servers:
            self.servers[server_id].stop_monitoring()
            del self.servers[server_id]
            print(f"Removed server '{server_id}'")
        else:
            print(f"Server '{server_id}' not found.")

    def start_all_monitoring(self):
        for s in self.servers.values():
            s.start_monitoring()

    def stop_all_monitoring(self):
        for s in self.servers.values():
            s.stop_monitoring()

    def show_cli(self):
        self.start_all_monitoring()
        print("\nNexusCtrl RDP Management CLI")
        print("Type 'help' for available commands.\n")

        while self.running:
            try:
                cmd_line = input("nexus> ").strip()
                if not cmd_line:
                    continue
                parts = cmd_line.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd == "help":
                    self._show_help()
                elif cmd == "add":
                    self._handle_add(args)
                elif cmd == "remove":
                    self._handle_remove(args)
                elif cmd == "list":
                    self._handle_list()
                elif cmd == "status":
                    self._handle_status(args)
                elif cmd == "monitor":
                    self._handle_monitor(args)
                elif cmd == "processes":
                    self._handle_processes(args)
                elif cmd == "kill":
                    self._handle_kill(args)
                elif cmd == "screen":
                    self._handle_screen(args)
                elif cmd == "task":
                    self._handle_task(args)
                elif cmd == "history":
                    self._handle_history(args)
                elif cmd == "exit":
                    print("Shutting down...")
                    self.running = False
                else:
                    print(f"Unknown command: {cmd}. Use 'help' for list.")
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
            except Exception as e:
                print(f"Error: {e}")

        self.stop_all_monitoring()

    def _show_help(self):
        print("""
Available commands:
  add <server_id> <host> [port]   - Add a new server (default port 9000)
  remove <server_id>              - Remove a server
  list                            - List all servers and their status
  status <server_id>              - Show detailed status and latest metrics
  monitor <server_id>             - Continuous live metrics update (press Ctrl+C to stop)
  processes <server_id>           - List running processes on server
  kill <server_id> <pid>          - Terminate a process on a server
  screen <server_id> [filename]   - Capture screen of server (save to file or display ascii?)
  task create <description> <priority>   - Create a task (priority: critical/high/medium/low)
  task list [priority] [status]         - List tasks, optionally filtered
  task update <task_id> <status>        - Update task status (pending/in-progress/completed)
  task delete <task_id>                - Delete a task
  history <server_id> [count]          - Show recent performance history
  help                             - Show this help
  exit                             - Exit the program
        """)

    def _handle_add(self, args):
        if len(args) < 2:
            print("Usage: add <server_id> <host> [port]")
            return
        sid = args[0]
        host = args[1]
        port = int(args[2]) if len(args) > 2 else 9000
        self.add_server(sid, host, port)

    def _handle_remove(self, args):
        if len(args) != 1:
            print("Usage: remove <server_id>")
            return
        self.remove_server(args[0])

    def _handle_list(self):
        print(f"{'ID':<15} {'Host':<20} {'Status':<10}")
        print("-" * 45)
        for sid, monitor in self.servers.items():
            print(f"{sid:<15} {monitor.agent_host}:{monitor.agent_port:<20} {monitor.status.value:<10}")

    def _handle_status(self, args):
        if len(args) != 1:
            print("Usage: status <server_id>")
            return
        sid = args[0]
        monitor = self.servers.get(sid)
        if not monitor:
            print(f"Server {sid} not found.")
            return
        print(f"Server: {sid}")
        print(f"Status: {monitor.status.value}")
        if monitor.status == ServerStatus.ONLINE:
            snapshot = monitor._fetch_metrics()
            if snapshot:
                print(f"CPU: {snapshot.cpu_percent}%")
                print(f"Memory: {snapshot.memory_percent:.1f}% (Available: {snapshot.memory_available // (1024*1024)} MB / Total: {snapshot.memory_total // (1024*1024)} MB)")
                print(f"Network sent: {snapshot.network_bytes_sent} bytes, recv: {snapshot.network_bytes_recv} bytes")
            else:
                print("Failed to fetch metrics.")
        else:
            print("Server is offline.")

    def _handle_monitor(self, args):
        if len(args) != 1:
            print("Usage: monitor <server_id>")
            return
        sid = args[0]
        monitor = self.servers.get(sid)
        if not monitor:
            print(f"Server {sid} not found.")
            return
        if monitor.status == ServerStatus.OFFLINE:
            print(f"Server {sid} is offline.")
            return
        print(f"Live monitoring {sid}. Press Ctrl+C to stop.")
        try:
            while True:
                snapshot = monitor._fetch_metrics()
                if snapshot:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] CPU: {snapshot.cpu_percent:5.1f}%  "
                          f"Mem: {snapshot.memory_percent:5.1f}%  "
                          f"Net sent: {snapshot.network_bytes_sent:10d}  recv: {snapshot.network_bytes_recv:10d}")
                else:
                    print("Failed to fetch metrics. Server might be offline.")
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            pass

    def _handle_processes(self, args):
        if len(args) != 1:
            print("Usage: processes <server_id>")
            return
        sid = args[0]
        monitor = self.servers.get(sid)
        if not monitor:
            print(f"Server {sid} not found.")
            return
        procs = monitor.get_processes()
        if not procs:
            print("No process data or server offline.")
            return
        print(f"{'PID':>8} {'Name':<20} {'CPU%':>8} {'Mem%':>8}")
        for p in procs[:30]:  # limit display
            print(f"{p.pid:8d} {p.name[:20]:<20} {p.cpu_percent:8.1f} {p.memory_percent:8.1f}")

    def _handle_kill(self, args):
        if len(args) != 2:
            print("Usage: kill <server_id> <pid>")
            return
        sid = args[0]
        try:
            pid = int(args[1])
        except ValueError:
            print("PID must be integer.")
            return
        monitor = self.servers.get(sid)
        if not monitor:
            print(f"Server {sid} not found.")
            return
        if monitor.kill_process(pid):
            print(f"Process {pid} killed on {sid}.")
        else:
            print(f"Failed to kill process {pid} on {sid}.")

    def _handle_screen(self, args):
        if len(args) < 1:
            print("Usage: screen <server_id> [filename]")
            return
        sid = args[0]
        filename = args[1] if len(args) > 1 else f"screen_{sid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        monitor = self.servers.get(sid)
        if not monitor:
            print(f"Server {sid} not found.")
            return
        img_bytes = monitor.get_screen_capture()
        if img_bytes:
            with open(filename, 'wb') as f:
                f.write(img_bytes)
            print(f"Screen capture saved to {filename} ({len(img_bytes)} bytes)")
        else:
            print("Failed to capture screen.")

    def _handle_task(self, args):
        if not args:
            print("Missing task subcommand. Use: task create/list/update/delete")
            return
        sub = args[0].lower()
        sub_args = args[1:]
        if sub == "create":
            if len(sub_args) < 2:
                print("Usage: task create <description> <priority>")
                return
            desc = sub_args[0]
            prio = sub_args[1]
            try:
                task = self.task_manager.create_task(desc, prio)
                print(f"Task #{task.task_id} created: {task.description} ({task.priority.name})")
            except ValueError as e:
                print(e)
        elif sub == "list":
            prio_filter = None
            status_filter = None
            # Parse optional filters
            if len(sub_args) > 0:
                prio_filter = sub_args[0].upper()
                if prio_filter not in [p.name for p in TaskPriority]:
                    prio_filter = None
            if len(sub_args) > 1:
                status_filter = sub_args[1].upper().replace('-', '_')
                if status_filter not in [s.name for s in TaskStatus]:
                    status_filter = None
            tasks = self.task_manager.list_tasks(prio_filter, status_filter)
            if not tasks:
                print("No tasks found.")
                return
            print(f"{'ID':<4} {'Status':<14} {'Priority':<10} {'Description':<30}")
            for t in tasks:
                print(f"{t.task_id:<4} {t.status.name:<14} {t.priority.name:<10} {t.description:<30}")
        elif sub == "update":
            if len(sub_args) != 2:
                print("Usage: task update <task_id> <status>")
                return
            try:
                tid = int(sub_args[0])
            except ValueError:
                print("Task ID must be integer.")
                return
            new_stat = sub_args[1]
            try:
                if self.task_manager.update_task_status(tid, new_stat):
                    print(f"Task #{tid} updated to {new_stat.upper()}.")
                else:
                    print(f"Task #{tid} not found.")
            except ValueError as e:
                print(e)
        elif sub == "delete":
            if len(sub_args) != 1:
                print("Usage: task delete <task_id>")
                return
            try:
                tid = int(sub_args[0])
            except ValueError:
                print("Task ID must be integer.")
                return
            if self.task_manager.delete_task(tid):
                print(f"Task #{tid} deleted.")
            else:
                print(f"Task #{tid} not found.")
        else:
            print(f"Unknown task subcommand: {sub}")

    def _handle_history(self, args):
        if len(args) < 1:
            print("Usage: history <server_id> [count]")
            return
        sid = args[0]
        count = int(args[1]) if len(args) > 1 else 10
        monitor = self.servers.get(sid)
        if not monitor:
            print(f"Server {sid} not found.")
            return
        history = monitor.get_history()
        if not history:
            print("No history data yet.")
            return
        recent = history[-count:]
        print(f"Last {len(recent)} metrics for {sid}:")
        print(f"{'Timestamp':<20} {'CPU%':>7} {'Mem%':>7} {'Net Sent':>12} {'Net Recv':>12}")
        for snap in recent:
            ts = snap.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{ts:<20} {snap.cpu_percent:7.1f} {snap.memory_percent:7.1f} {snap.network_bytes_sent:12d} {snap.network_bytes_recv:12d}")


# --------------------- Entry Point --------------------- #
def run_agent(port: int):
    """Run the agent as a background service."""
    agent = AgentServer(port=port)
    agent.start()
    print("Agent started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
        agent.stop()


def main():
    parser = argparse.ArgumentParser(description="NexusCtrl - Personal RDP Server Management Tool")
    parser.add_argument("--agent", action="store_true", help="Run as an agent")
    parser.add_argument("--port", type=int, default=9000, help="Agent listening port (default: 9000)")
    args = parser.parse_args()

    if args.agent:
        run_agent(args.port)
    else:
        ctrl = NexusCtrl()
        ctrl.show_cli()


if __name__ == "__main__":
    main()