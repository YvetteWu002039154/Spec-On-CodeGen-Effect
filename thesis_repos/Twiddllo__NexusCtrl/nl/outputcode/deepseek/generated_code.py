import socket
import threading
import time
import json
import base64
import cmd
import sys
import os
import signal
from collections import deque
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

try:
    import psutil
except ImportError:
    psutil = None

try:
    import PIL.ImageGrab
except ImportError:
    PIL = None


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Task:
    _id_counter = 0

    def __init__(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM,
                 assigned_server: Optional[str] = None):
        Task._id_counter += 1
        self.id = Task._id_counter
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.assigned_server = assigned_server

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority.name,
            "status": self.status.value,
            "assigned_server": self.assigned_server,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


class MetricsHistory:
    MAX_HISTORY = 100

    def __init__(self):
        self._history: deque = deque(maxlen=MetricsHistory.MAX_HISTORY)

    def add(self, metrics: Dict[str, float]):
        entry = {"timestamp": time.time(), **metrics}
        self._history.append(entry)

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        if limit is None:
            return list(self._history)
        return list(self._history)[-limit:]


class ServerState:
    def __init__(self, name: str, addr: Tuple[str, int]):
        self.name = name
        self.addr = addr
        self.online = True
        self.last_seen = time.time()
        self.last_metrics: Dict[str, float] = {}
        self.last_processes: List[Tuple[int, str]] = []
        self.last_screenshot: Optional[bytes] = None
        self.metrics_history = MetricsHistory()
        self.agent_socket: Optional[socket.socket] = None
        self.lock = threading.Lock()

    def update_metrics(self, metrics: Dict[str, float]):
        with self.lock:
            self.last_metrics = metrics
            self.metrics_history.add(metrics)
            self.last_seen = time.time()

    def update_processes(self, processes: List[Tuple[int, str]]):
        with self.lock:
            self.last_processes = processes
            self.last_seen = time.time()

    def set_screenshot(self, img_data: bytes):
        with self.lock:
            self.last_screenshot = img_data
            self.last_seen = time.time()

    def set_offline(self):
        with self.lock:
            self.online = False

    def is_online(self) -> bool:
        return self.online


class Agent:
    AGENT_PORT = 9998
    METRICS_INTERVAL = 5

    def __init__(self, server_host: str, server_port: int = AGENT_PORT, name: str = None):
        self.server_host = server_host
        self.server_port = server_port
        self.name = name or socket.gethostname()
        self.sock: Optional[socket.socket] = None
        self.running = False

    def _get_cpu_percent(self) -> float:
        if psutil:
            return psutil.cpu_percent(interval=0.5)
        return 50.0

    def _get_ram_usage(self) -> float:
        if psutil:
            mem = psutil.virtual_memory()
            return mem.percent
        return 60.0

    def _get_network_usage(self) -> Tuple[float, float]:
        if psutil:
            net = psutil.net_io_counters()
            return net.bytes_sent / (1024 * 1024), net.bytes_recv / (1024 * 1024)  # Convert to MB
        return 100.0, 50.0

    def collect_metrics(self) -> Dict[str, float]:
        cpu = self._get_cpu_percent()
        ram = self._get_ram_usage()
        net_sent, net_recv = self._get_network_usage()
        return {"cpu": cpu, "ram": ram, "net_sent": net_sent, "net_recv": net_recv}

    def get_processes(self) -> List[Tuple[int, str]]:
        if psutil:
            return [(p.pid, p.name()) for p in psutil.process_iter(['pid', 'name'])]
        return [(1, "System"), (100, "agent"), (200, "notepad")]

    def capture_screen(self) -> Optional[bytes]:
        if PIL:
            import io
            img = PIL.ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return buf.getvalue()
        return None

    def kill_process(self, pid: int) -> bool:
        if psutil:
            try:
                p = psutil.Process(pid)
                p.terminate()
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        return pid % 2 == 0  # Simulate success for even pids

    def _send_line(self, line: str):
        if self.sock:
            self.sock.sendall((line + "\n").encode())

    def _recv_line(self) -> str:
        buffer = b""
        while not buffer.endswith(b"\n"):
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Connection closed")
            buffer += chunk
        return buffer.decode().strip()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_host, self.server_port))
        self._send_line(f"REGISTER {self.name}")
        resp = self._recv_line()
        if resp != "OK":
            raise ConnectionError(f"Registration failed: {resp}")

    def start(self):
        self.running = True
        self.connect()
        print(f"[Agent] Connected to server as {self.name}")
        metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        metrics_thread.start()
        self._command_loop()

    def _metrics_loop(self):
        while self.running:
            time.sleep(Metrics.METRICS_INTERVAL)
            if not self.running:
                break
            try:
                metrics = self.collect_metrics()
                msg = "METRICS " + ",".join(f"{k}={v}" for k, v in metrics.items())
                self._send_line(msg)
            except Exception as e:
                print(f"[Agent] Metrics send error: {e}")
                self.running = False
                break

    def _command_loop(self):
        while self.running:
            try:
                msg = self._recv_line()
                if msg.startswith("PROCESSES"):
                    procs = self.get_processes()
                    # Format: pid1:name1,pid2:name2,...
                    data = ",".join(f"{pid}:{name}" for pid, name in procs)
                    self._send_line(f"PROCESS_LIST {data}")
                elif msg.startswith("SCREENSHOT"):
                    img = self.capture_screen()
                    if img:
                        encoded = base64.b64encode(img).decode()
                        self._send_line(f"SCREENSHOT {encoded}")
                    else:
                        self._send_line("SCREENSHOT ERROR")
                elif msg.startswith("KILL "):
                    parts = msg.split()
                    if len(parts) == 2:
                        pid = int(parts[1])
                        success = self.kill_process(pid)
                        if success:
                            self._send_line(f"KILL_OK {pid}")
                        else:
                            self._send_line(f"KILL_FAIL {pid}")
                    else:
                        self._send_line("ERROR invalid kill")
                else:
                    self._send_line("ERROR unknown command")
            except Exception as e:
                print(f"[Agent] Command loop error: {e}")
                self.running = False
                break
        self.sock.close()


class NexusCtrlServer(cmd.Cmd):
    AGENT_LISTEN = ('0.0.0.0', 9998)

    def __init__(self):
        super().__init__()
        self.prompt = "NexusCtrl> "
        self.servers: Dict[str, ServerState] = {}
        self.tasks: Dict[int, Task] = {}
        self.agent_listener_thread: Optional[threading.Thread] = None
        self.servers_lock = threading.Lock()

    # --- Cmd commands ---

    def do_servers(self, arg):
        """List all connected servers and their status."""
        with self.servers_lock:
            if not self.servers:
                print("No servers connected.")
                return
            print(f"{'Name':<20} {'Online':<8} {'CPU':<8} {'RAM':<8} {'Net Sent (MB)':<15} {'Net Recv (MB)':<15}")
            for name, server in self.servers.items():
                cpu = server.last_metrics.get("cpu", 0)
                ram = server.last_metrics.get("ram", 0)
                net_sent = server.last_metrics.get("net_sent", 0)
                net_recv = server.last_metrics.get("net_recv", 0)
                status = "Yes" if server.is_online() else "No"
                print(f"{name:<20} {status:<8} {cpu:<8.1f} {ram:<8.1f} {net_sent:<15.2f} {net_recv:<15.2f}")

    def do_processes(self, arg):
        """List processes on a server: processes <server_name>"""
        if not arg:
            print("Usage: processes <server_name>")
            return
        name = arg.strip()
        with self.servers_lock:
            server = self.servers.get(name)
            if not server:
                print(f"Server '{name}' not found.")
                return
            if not server.is_online():
                print(f"Server '{name}' is offline.")
                return
            # Request process list from agent
            if server.agent_socket:
                try:
                    server.agent_socket.sendall("PROCESSES\n".encode())
                    response = self._recv_from_agent(server)
                    if response.startswith("PROCESS_LIST "):
                        data = response[len("PROCESS_LIST "):]
                        if data:
                            procs = [item.split(":", 1) for item in data.split(",")]
                            server.update_processes([(int(pid), name) for pid, name in procs])
                    else:
                        print("Error retrieving process list.")
                        return
                except Exception as e:
                    print(f"Communication error: {e}")
                    server.set_offline()
                    return
            processes = server.last_processes
            if not processes:
                print("No process data available.")
                return
            print(f"Processes on {name}:")
            for pid, proc_name in processes:
                print(f"  PID: {pid:<8} Name: {proc_name}")

    def do_kill(self, arg):
        """Kill a process on a server: kill <server_name> <pid>"""
        parts = arg.split()
        if len(parts) != 2:
            print("Usage: kill <server_name> <pid>")
            return
        server_name, pid_str = parts
        try:
            pid = int(pid_str)
        except ValueError:
            print("Invalid PID.")
            return
        with self.servers_lock:
            server = self.servers.get(server_name)
            if not server:
                print(f"Server '{server_name}' not found.")
                return
            if not server.is_online():
                print(f"Server '{server_name}' is offline.")
                return
            if server.agent_socket:
                try:
                    server.agent_socket.sendall(f"KILL {pid}\n".encode())
                    response = self._recv_from_agent(server)
                    if response.startswith("KILL_OK"):
                        print(f"Process {pid} terminated.")
                    elif response.startswith("KILL_FAIL"):
                        print(f"Failed to terminate process {pid}.")
                    else:
                        print(f"Unexpected response: {response}")
                except Exception as e:
                    print(f"Communication error: {e}")
                    server.set_offline()
            else:
                print("No agent connection.")

    def do_screenshot(self, arg):
        """Request screenshot from server: screenshot <server_name> [filename]"""
        parts = arg.split()
        if not parts:
            print("Usage: screenshot <server_name> [filename]")
            return
        server_name = parts[0]
        filename = parts[1] if len(parts) > 1 else f"{server_name}_screenshot.png"
        with self.servers_lock:
            server = self.servers.get(server_name)
            if not server:
                print(f"Server '{server_name}' not found.")
                return
            if not server.is_online():
                print(f"Server '{server_name}' is offline.")
                return
            if server.agent_socket:
                try:
                    server.agent_socket.sendall("SCREENSHOT\n".encode())
                    response = self._recv_from_agent(server)
                    if response.startswith("SCREENSHOT "):
                        img_data = base64.b64decode(response[len("SCREENSHOT "):])
                        with open(filename, 'wb') as f:
                            f.write(img_data)
                        server.set_screenshot(img_data)
                        print(f"Screenshot saved to {filename}")
                    else:
                        print("Failed to capture screenshot.")
                except Exception as e:
                    print(f"Communication error: {e}")
                    server.set_offline()
            else:
                print("No agent connection.")

    def do_tasks(self, arg):
        """List all tasks."""
        if not self.tasks:
            print("No tasks.")
            return
        for task in self.tasks.values():
            info = task.to_dict()
            print(f"ID: {info['id']}, Desc: {info['description']}, Priority: {info['priority']}, "
                  f"Status: {info['status']}, Server: {info['assigned_server']}")

    def do_add_task(self, arg):
        """Add a new task: add_task <description> <priority(CRITICAL,HIGH,MEDIUM,LOW)> [server]"""
        parts = arg.split(maxsplit=2)
        if len(parts) < 2:
            print("Usage: add_task <description> <priority> [server]")
            return
        desc = parts[0]
        priority_str = parts[1].upper()
        try:
            priority = TaskPriority[priority_str]
        except KeyError:
            print("Invalid priority. Use CRITICAL, HIGH, MEDIUM, or LOW.")
            return
        server = parts[2] if len(parts) > 2 else None
        task = Task(desc, priority, server)
        self.tasks[task.id] = task
        print(f"Task {task.id} created.")

    def do_update_task(self, arg):
        """Update task status: update_task <id> <status(PENDING,IN_PROGRESS,COMPLETED)>"""
        parts = arg.split()
        if len(parts) != 2:
            print("Usage: update_task <id> <status>")
            return
        try:
            tid = int(parts[0])
        except ValueError:
            print("Invalid task ID.")
            return
        status_str = parts[1].upper()
        try:
            status = TaskStatus[status_str]
        except KeyError:
            print("Invalid status. Use PENDING, IN_PROGRESS, or COMPLETED.")
            return
        task = self.tasks.get(tid)
        if not task:
            print(f"Task {tid} not found.")
            return
        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = time.time()
        print(f"Task {tid} updated to {status.value}.")

    def do_history(self, arg):
        """Show performance history for a server: history <server_name> [limit]"""
        parts = arg.split()
        if not parts:
            print("Usage: history <server_name> [limit]")
            return
        server_name = parts[0]
        limit = None
        if len(parts) > 1:
            try:
                limit = int(parts[1])
            except ValueError:
                print("Invalid limit.")
                return
        with self.servers_lock:
            server = self.servers.get(server_name)
            if not server:
                print(f"Server '{server_name}' not found.")
                return
            history = server.metrics_history.get_history(limit)
            if not history:
                print("No history available.")
                return
            print(f"History for {server_name} (most recent first):")
            for entry in reversed(history):
                ts = entry["timestamp"]
                cpu = entry.get("cpu", 0)
                ram = entry.get("ram", 0)
                print(f"  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))} - CPU: {cpu:.1f}%, RAM: {ram:.1f}%")

    def do_help(self, arg):
        """Show available commands."""
        print("Available commands:")
        print("  servers                     - List all servers")
        print("  processes <server>          - List processes on a server")
        print("  kill <server> <pid>         - Kill process on server")
        print("  screenshot <server> [file]  - Capture screenshot from server")
        print("  tasks                       - List tasks")
        print("  add_task <desc> <prio> [srv]- Add task")
        print("  update_task <id> <status>   - Update task status")
        print("  history <server> [limit]    - Show performance history")
        print("  exit/quit                   - Shutdown server")
        print("  help                        - This help")
        # Override default help

    def do_exit(self, arg):
        """Shutdown the NexusCtrl server."""
        print("Shutting down...")
        self._shutdown()
        return True

    def do_quit(self, arg):
        """Alias for exit."""
        return self.do_exit(arg)

    # --- Agent connection handling ---

    def _recv_from_agent(self, server: ServerState) -> str:
        buffer = b""
        while not buffer.endswith(b"\n"):
            chunk = server.agent_socket.recv(1024)
            if not chunk:
                raise ConnectionError("Agent disconnected")
            buffer += chunk
        return buffer.decode().strip()

    def handle_agent_client(self, client_sock: socket.socket, addr: Tuple[str, int]):
        try:
            # Expect REGISTER <name>
            data = client_sock.recv(1024).decode()
            if not data.startswith("REGISTER "):
                client_sock.sendall("ERROR invalid registration\n".encode())
                client_sock.close()
                return
            name = data[len("REGISTER "):].strip()
            with self.servers_lock:
                # If server already exists, update connection
                if name in self.servers:
                    old = self.servers[name]
                    old.online = True
                    old.agent_socket.close() if old.agent_socket else None
                    old.agent_socket = client_sock
                    old.addr = addr
                    old.last_seen = time.time()
                else:
                    server = ServerState(name, addr)
                    server.agent_socket = client_sock
                    self.servers[name] = server
            client_sock.sendall("OK\n".encode())
            print(f"[Server] Agent '{name}' connected from {addr}")
            # Now handle messages from this agent
            buffer = b""
            while True:
                chunk = client_sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.startswith(b"METRICS "):
                        self._handle_metrics(name, line[len(b"METRICS "):].decode())
                    elif line.startswith(b"PROCESS_LIST ") or line.startswith(b"SCREENSHOT ") or \
                         line.startswith(b"KILL_OK") or line.startswith(b"KILL_FAIL"):
                        # These are responses to server commands; agent only sends METRICS spontaneously.
                        pass
                    else:
                        print(f"[Server] Unknown agent message from {name}: {line}")
        except Exception as e:
            print(f"[Server] Agent {name} error: {e}")
        finally:
            with self.servers_lock:
                if name in self.servers:
                    self.servers[name].set_offline()
                    self.servers[name].agent_socket = None
            client_sock.close()
            print(f"[Server] Agent '{name}' disconnected.")

    def _handle_metrics(self, server_name: str, data: str):
        metrics = {}
        for item in data.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                try:
                    metrics[k] = float(v)
                except ValueError:
                    pass
        with self.servers_lock:
            server = self.servers.get(server_name)
            if server:
                server.update_metrics(metrics)

    def agent_listener(self):
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind(self.AGENT_LISTEN)
        listen_sock.listen(5)
        print(f"[Server] Listening for agents on {self.AGENT_LISTEN}")
        while True:
            try:
                client_sock, addr = listen_sock.accept()
                threading.Thread(target=self.handle_agent_client, args=(client_sock, addr), daemon=True).start()
            except Exception as e:
                print(f"[Server] Accept error: {e}")
                break
        listen_sock.close()

    def _shutdown(self):
        # Close all agent sockets
        with self.servers_lock:
            for server in self.servers.values():
                if server.agent_socket:
                    try:
                        server.agent_socket.close()
                    except:
                        pass
        # Terminate listener thread? It's daemon, will exit with main.

    def start(self):
        self.agent_listener_thread = threading.Thread(target=self.agent_listener, daemon=True)
        self.agent_listener_thread.start()
        print("NexusCtrl Server started. Type help for commands.")
        self.cmdloop()


def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "--agent":
            host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
            port = int(sys.argv[3]) if len(sys.argv) > 3 else 9998
            name = sys.argv[4] if len(sys.argv) > 4 else None
            agent = Agent(host, port, name)
            agent.start()
        else:
            print("Usage: python nexusctrl.py [--agent <host> [port] [name]]")
            sys.exit(1)
    else:
        server = NexusCtrlServer()
        server.start()


if __name__ == "__main__":
    main()