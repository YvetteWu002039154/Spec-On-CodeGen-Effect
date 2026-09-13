import os
import sys
import time
import json
import base64
import io
import enum
import socket
import threading
import datetime
from typing import Optional, Dict, List, Any, Union

# External dependencies: psutil, Pillow, mss (optional for cross-platform screenshots)
try:
    import psutil
except ImportError:
    print("psutil is required. Install it with: pip install psutil")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Pillow is required. Install it with: pip install Pillow")
    sys.exit(1)

# Attempt to import screenshot library; prefer pyautogui for ease, fallback to mss
try:
    import pyautogui
    SCREENSHOT_LIB = "pyautogui"
except ImportError:
    try:
        import mss
        SCREENSHOT_LIB = "mss"
    except ImportError:
        print("Either pyautogui or mss is required for screen capture. Install with: pip install pyautogui or pip install mss")
        SCREENSHOT_LIB = None


class Priority(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Task:
    _id_counter = 0

    def __init__(self, description: str, priority: Priority):
        Task._id_counter += 1
        self.id = Task._id_counter
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.datetime.now()

    def complete(self):
        self.status = TaskStatus.COMPLETED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat()
        }

    def __repr__(self):
        return f"Task({self.id}): {self.description} [{self.priority.value}] - {self.status.value}"


class PerformanceData:
    def __init__(self, cpu: float, memory: float, network_sent: int, network_recv: int, processes_count: int):
        self.timestamp = datetime.datetime.now()
        self.cpu = cpu
        self.memory = memory
        self.network_sent = network_sent
        self.network_recv = network_recv
        self.processes_count = processes_count

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu": self.cpu,
            "memory": self.memory,
            "network_sent": self.network_sent,
            "network_recv": self.network_recv,
            "processes_count": self.processes_count
        }


class Agent:
    """Runs on target machine, collects system metrics and responds to commands."""
    def __init__(self, bind_port: int = 9999):
        self.bind_port = bind_port
        self.server_socket = None
        self.running = False
        self._thread = None

    def _handle_client(self, conn: socket.socket, addr):
        print(f"[Agent] Connection from {addr}")
        try:
            while self.running:
                # Read command length header (4 bytes big-endian)
                header = conn.recv(4)
                if not header:
                    break
                length = int.from_bytes(header, 'big')
                if length == 0:
                    break
                data = b''
                while len(data) < length:
                    chunk = conn.recv(length - len(data))
                    if not chunk:
                        break
                    data += chunk
                if len(data) != length:
                    break

                command = json.loads(data.decode('utf-8'))
                response = self._process_command(command)
                response_bytes = json.dumps(response).encode('utf-8')

                # Send response length header + response
                conn.sendall(len(response_bytes).to_bytes(4, 'big'))
                conn.sendall(response_bytes)
        except Exception as e:
            print(f"[Agent] Error handling client {addr}: {e}")
        finally:
            conn.close()

    def _process_command(self, command: dict) -> dict:
        action = command.get("action")
        params = command.get("params", {})

        if action == "get_cpu":
            return {"status": "ok", "data": psutil.cpu_percent(interval=0.1)}
        elif action == "get_ram":
            mem = psutil.virtual_memory()
            return {"status": "ok", "data": mem.percent}
        elif action == "get_network":
            net = psutil.net_io_counters()
            return {"status": "ok", "data": {"sent": net.bytes_sent, "recv": net.bytes_recv}}
        elif action == "get_processes":
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return {"status": "ok", "data": procs}
        elif action == "kill_process":
            pid = params.get("pid")
            if pid is None:
                return {"status": "error", "message": "No PID provided"}
            try:
                p = psutil.Process(pid)
                p.kill()
                return {"status": "ok", "message": f"Process {pid} killed"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif action == "screenshot":
            if SCREENSHOT_LIB is None:
                return {"status": "error", "message": "No screenshot library available"}
            try:
                img_bytes = None
                if SCREENSHOT_LIB == "pyautogui":
                    img = pyautogui.screenshot()
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    img_bytes = buf.getvalue()
                elif SCREENSHOT_LIB == "mss":
                    with mss.mss() as sct:
                        # Grab the first monitor
                        screenshot = sct.grab(sct.monitors[1])
                        # Convert to PIL Image
                        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                        buf = io.BytesIO()
                        img.save(buf, format='PNG')
                        img_bytes = buf.getvalue()
                encoded = base64.b64encode(img_bytes).decode('utf-8')
                return {"status": "ok", "data": encoded}
            except Exception as e:
                return {"status": "error", "message": f"Screenshot failed: {e}"}
        elif action == "ping":
            return {"status": "ok", "message": "pong"}
        else:
            return {"status": "error", "message": "Unknown command"}

    def start(self):
        if self.running:
            return
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.bind_port))
        self.server_socket.listen(5)
        self.running = True
        print(f"[Agent] Listening on port {self.bind_port}")
        self._thread = threading.Thread(target=self._accept_connections, daemon=True)
        self._thread.start()

    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                t = threading.Thread(target=self._handle_client, args=(conn, addr))
                t.daemon = True
                t.start()
            except Exception as e:
                if self.running:
                    print(f"[Agent] Accept error: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self._thread:
            self._thread.join(timeout=2)


class AgentConnection:
    """Represents a remote agent managed by the central server."""
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.online = False
        self.last_seen = None
        self.socket = None
        self.lock = threading.Lock()

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.online = True
            self.last_seen = datetime.datetime.now()
            return True
        except Exception as e:
            self.online = False
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.online = False

    def send_command(self, command: dict) -> dict:
        """Send a command to the agent and return its response. Must hold lock."""
        if not self.online or not self.socket:
            return {"status": "error", "message": "Agent offline"}
        try:
            request_bytes = json.dumps(command).encode('utf-8')
            # Send header
            self.socket.sendall(len(request_bytes).to_bytes(4, 'big'))
            self.socket.sendall(request_bytes)

            # Read response length header
            header = self.socket.recv(4)
            if not header:
                raise ConnectionError("Connection closed")
            length = int.from_bytes(header, 'big')
            data = b''
            while len(data) < length:
                chunk = self.socket.recv(length - len(data))
                if not chunk:
                    raise ConnectionError("Connection closed")
                data += chunk
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            self.online = False
            return {"status": "error", "message": str(e)}

    def update_online_status(self) -> bool:
        """Ping the agent to check if still online."""
        if not self.socket:
            return False
        with self.lock:
            resp = self.send_command({"action": "ping"})
            if resp.get("status") == "ok":
                self.online = True
                self.last_seen = datetime.datetime.now()
                return True
            else:
                self.online = False
                return False


class CentralServer:
    """Main management hub that coordinates agents and tasks."""
    def __init__(self):
        self.agents: Dict[str, AgentConnection] = {}  # key: "host:port"
        self.tasks: List[Task] = []
        self.history: List[PerformanceData] = []  # aggregate or per agent; we store all with agent id
        self.running = False
        self._monitor_thread = None
        self._history_size = 100  # keep last 100 samples

    def add_agent(self, host: str, port: int = 9999) -> str:
        key = f"{host}:{port}"
        if key in self.agents:
            return f"Agent {key} already exists"
        conn = AgentConnection(host, port)
        if conn.connect():
            self.agents[key] = conn
            return f"Agent {key} added and connected successfully."
        else:
            self.agents[key] = conn  # keep offline
            return f"Agent {key} added but connection failed. It is offline."

    def remove_agent(self, host: str, port: int = 9999):
        key = f"{host}:{port}"
        if key in self.agents:
            self.agents[key].disconnect()
            del self.agents[key]

    def get_agent_statuses(self) -> List[dict]:
        result = []
        for key, agent in self.agents.items():
            result.append({
                "agent_id": key,
                "online": agent.online,
                "last_seen": agent.last_seen.isoformat() if agent.last_seen else None
            })
        return result

    def collect_performance(self, host: str, port: int = 9999) -> Optional[PerformanceData]:
        key = f"{host}:{port}"
        agent = self.agents.get(key)
        if not agent:
            return None
        with agent.lock:
            cpu_resp = agent.send_command({"action": "get_cpu"})
            ram_resp = agent.send_command({"action": "get_ram"})
            net_resp = agent.send_command({"action": "get_network"})
            proc_resp = agent.send_command({"action": "get_processes"})
            if any(r.get("status") != "ok" for r in [cpu_resp, ram_resp, net_resp, proc_resp]):
                return None
            cpu = cpu_resp["data"]
            mem = ram_resp["data"]
            sent = net_resp["data"]["sent"]
            recv = net_resp["data"]["recv"]
            procs_count = len(proc_resp["data"])
            perf = PerformanceData(cpu, mem, sent, recv, procs_count)
            self.history.append(perf)
            if len(self.history) > self._history_size:
                self.history.pop(0)
            return perf

    def get_processes(self, host: str, port: int = 9999) -> list:
        key = f"{host}:{port}"
        agent = self.agents.get(key)
        if not agent:
            return []
        with agent.lock:
            resp = agent.send_command({"action": "get_processes"})
            if resp.get("status") == "ok":
                return resp["data"]
            return []

    def kill_process(self, host: str, port: int, pid: int) -> dict:
        key = f"{host}:{port}"
        agent = self.agents.get(key)
        if not agent:
            return {"status": "error", "message": "Agent not found"}
        with agent.lock:
            return agent.send_command({"action": "kill_process", "params": {"pid": pid}})

    def get_screenshot(self, host: str, port: int) -> Union[bytes, None]:
        key = f"{host}:{port}"
        agent = self.agents.get(key)
        if not agent:
            return None
        with agent.lock:
            resp = agent.send_command({"action": "screenshot"})
            if resp.get("status") == "ok":
                encoded = resp["data"]
                return base64.b64decode(encoded)
            return None

    # Task management
    def create_task(self, description: str, priority: Priority) -> Task:
        task = Task(description, priority)
        self.tasks.append(task)
        return task

    def complete_task(self, task_id: int) -> bool:
        for task in self.tasks:
            if task.id == task_id:
                task.complete()
                return True
        return False

    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        if status_filter:
            return [t for t in self.tasks if t.status == status_filter]
        return self.tasks

    def monitor_loop(self, interval: float = 5.0):
        """Background thread that periodically checks agent online status and collects metrics."""
        while self.running:
            for key, agent in list(self.agents.items()):
                # Check online status
                agent.update_online_status()
                # If online, collect performance
                if agent.online:
                    host, port = key.split(':')
                    self.collect_performance(host, int(port))
            time.sleep(interval)

    def start_monitoring(self, interval: float = 5.0):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self.running = True
        self._monitor_thread = threading.Thread(target=self.monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self.running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        for agent in self.agents.values():
            agent.disconnect()


def print_help():
    print("""
NexusCtrl - RDP Server Management Tool
Commands:
  add_agent <host> [port]    - Add and connect to a new agent (default port 9999)
  remove_agent <host> [port] - Disconnect and remove an agent
  agents                     - List all registered agents and their status
  perf <host> [port]         - Collect and display performance data from agent
  processes <host> [port]   - List active processes on agent
  kill <host> <port> <pid>   - Kill a process on agent
  screenshot <host> [port]   - Capture screenshot from agent (saves to screenshot.png)
  task add <desc> <priority> - Create a new task (priority: critical/high/medium/low)
  task list [status]         - List tasks (optional filter: pending/completed)
  task complete <id>         - Mark task as completed
  history                    - Show recent performance history
  monitor <interval>         - Start/stop background monitoring (seconds)
  help                       - Show this help
  exit                       - Exit
""")


def main():
    server = CentralServer()
    print("NexusCtrl Central Server started. Type 'help' for commands.")
    monitor_interval = 5.0
    monitoring = False

    while True:
        try:
            cmd = input("nexus> ").strip()
            if not cmd:
                continue
            parts = cmd.split()
            action = parts[0].lower()

            if action == "add_agent":
                if len(parts) < 2:
                    print("Usage: add_agent <host> [port]")
                    continue
                host = parts[1]
                port = int(parts[2]) if len(parts) > 2 else 9999
                msg = server.add_agent(host, port)
                print(msg)
            elif action == "remove_agent":
                if len(parts) < 2:
                    print("Usage: remove_agent <host> [port]")
                    continue
                host = parts[1]
                port = int(parts[2]) if len(parts) > 2 else 9999
                server.remove_agent(host, port)
                print(f"Agent {host}:{port} removed.")
            elif action == "agents":
                statuses = server.get_agent_statuses()
                if not statuses:
                    print("No agents registered.")
                else:
                    for s in statuses:
                        print(f"{s['agent_id']} - {'ONLINE' if s['online'] else 'OFFLINE'} (last seen: {s['last_seen'] or 'N/A'})")
            elif action == "perf":
                if len(parts) < 2:
                    print("Usage: perf <host> [port]")
                    continue
                host = parts[1]
                port = int(parts[2]) if len(parts) > 2 else 9999
                perf = server.collect_performance(host, port)
                if perf:
                    print(f"CPU: {perf.cpu}%, RAM: {perf.memory}%, Network: {perf.network_sent}B sent / {perf.network_recv}B recv, Processes: {perf.processes_count}")
                else:
                    print("Failed to collect performance data (agent offline or error).")
            elif action == "processes":
                if len(parts) < 2:
                    print("Usage: processes <host> [port]")
                    continue
                host = parts[1]
                port = int(parts[2]) if len(parts) > 2 else 9999
                procs = server.get_processes(host, port)
                if procs:
                    print(f"Showing top 20 processes on {host}:{port}:")
                    for p in sorted(procs, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:20]:
                        print(f"PID {p['pid']} {p['name']} CPU: {p.get('cpu_percent',0)}% MEM: {p.get('memory_percent',0)}%")
                else:
                    print("No processes retrieved or agent offline.")
            elif action == "kill":
                if len(parts) < 4:
                    print("Usage: kill <host> <port> <pid>")
                    continue
                host = parts[1]
                port = int(parts[2])
                pid = int(parts[3])
                resp = server.kill_process(host, port, pid)
                print(resp.get("message", resp.get("status")))
            elif action == "screenshot":
                if len(parts) < 2:
                    print("Usage: screenshot <host> [port]")
                    continue
                host = parts[1]
                port = int(parts[2]) if len(parts) > 2 else 9999
                img_bytes = server.get_screenshot(host, port)
                if img_bytes:
                    filename = f"screenshot_{host}_{port}.png"
                    with open(filename, 'wb') as f:
                        f.write(img_bytes)
                    print(f"Screenshot saved as {filename}")
                else:
                    print("Failed to capture screenshot.")
            elif action == "task":
                if len(parts) < 2:
                    print("Usage: task add <desc> <priority> | task list [status] | task complete <id>")
                    continue
                sub = parts[1].lower()
                if sub == "add":
                    if len(parts) < 4:
                        print("Usage: task add <desc> <priority>")
                        continue
                    desc = parts[2]
                    prio_str = parts[3].lower()
                    try:
                        priority = Priority(prio_str)
                    except ValueError:
                        print("Priority must be one of: critical, high, medium, low")
                        continue
                    task = server.create_task(desc, priority)
                    print(f"Task created: {task}")
                elif sub == "list":
                    filt = None
                    if len(parts) > 2:
                        status_str = parts[2].lower()
                        try:
                            filt = TaskStatus(status_str)
                        except ValueError:
                            print("Status filter must be: pending or completed")
                            continue
                    tasks = server.list_tasks(filt)
                    if tasks:
                        for t in tasks:
                            print(t)
                    else:
                        print("No tasks found.")
                elif sub == "complete":
                    if len(parts) < 3:
                        print("Usage: task complete <id>")
                        continue
                    task_id = int(parts[2])
                    if server.complete_task(task_id):
                        print(f"Task {task_id} marked as completed.")
                    else:
                        print(f"Task {task_id} not found.")
                else:
                    print("Unknown task command.")
            elif action == "history":
                hist = server.history
                if not hist:
                    print("No performance history recorded yet.")
                else:
                    for h in hist[-10:]:
                        print(f"{h.timestamp.strftime('%H:%M:%S')} - CPU: {h.cpu}% RAM: {h.memory}% Net: {h.network_sent}/{h.network_recv}B Proc: {h.processes_count}")
            elif action == "monitor":
                if len(parts) < 2:
                    print("Usage: monitor <interval in seconds> (0 to stop)")
                    continue
                interval = float(parts[1])
                if interval <= 0:
                    if monitoring:
                        server.stop()
                        monitoring = False
                        print("Monitoring stopped.")
                    else:
                        print("Not currently monitoring.")
                else:
                    if monitoring:
                        # Restart with new interval
                        server.stop()
                    server.start_monitoring(interval)
                    monitoring = True
                    print(f"Background monitoring started with interval {interval}s")
            elif action == "help":
                print_help()
            elif action == "exit":
                print("Shutting down...")
                server.stop()
                break
            else:
                print("Unknown command. Type 'help'.")
        except KeyboardInterrupt:
            print("\nShutting down...")
            server.stop()
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    # Check if we should run as agent
    if len(sys.argv) > 1 and sys.argv[1] == "--agent":
        port = 9999
        if len(sys.argv) > 2:
            port = int(sys.argv[2])
        agent = Agent(bind_port=port)
        agent.start()
        print("Agent running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            agent.stop()
    else:
        main()