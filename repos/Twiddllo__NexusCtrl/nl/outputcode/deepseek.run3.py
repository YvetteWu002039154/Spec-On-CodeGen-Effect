import json
import struct
import threading
import time
import socket
import sys
import io
import base64
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque

try:
    import psutil
except ImportError:
    psutil = None

try:
    import mss
except ImportError:
    mss = None
    try:
        from PIL import ImageGrab
    except ImportError:
        ImageGrab = None

# -------------------------------
# Data classes
# -------------------------------

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0

    def to_dict(self):
        return {'pid': self.pid, 'name': self.name,
                'cpu_percent': self.cpu_percent, 'memory_mb': self.memory_mb}

    @staticmethod
    def from_dict(d):
        return ProcessInfo(d['pid'], d['name'], d['cpu_percent'], d['memory_mb'])


@dataclass
class MonitoringData:
    cpu_percent: float
    ram_percent: float
    ram_total_gb: float
    ram_used_gb: float
    network_sent_kbps: float = 0.0
    network_recv_kbps: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {'cpu_percent': self.cpu_percent,
                'ram_percent': self.ram_percent,
                'ram_total_gb': self.ram_total_gb,
                'ram_used_gb': self.ram_used_gb,
                'network_sent_kbps': self.network_sent_kbps,
                'network_recv_kbps': self.network_recv_kbps,
                'timestamp': self.timestamp}

    @staticmethod
    def from_dict(d):
        return MonitoringData(d['cpu_percent'], d['ram_percent'],
                              d['ram_total_gb'], d['ram_used_gb'],
                              d['network_sent_kbps'], d['network_recv_kbps'],
                              d['timestamp'])


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    completed: bool = False
    created_at: float = field(default_factory=time.time)


# -------------------------------
# System utilities
# -------------------------------

class SystemMonitor:
    def __init__(self):
        self._prev_net = psutil.net_io_counters() if psutil else None
        self._prev_time = time.time()

    def get_cpu_percent(self) -> float:
        if psutil:
            return psutil.cpu_percent(interval=0.1)
        return 0.0

    def get_ram_info(self) -> Tuple[float, float, float]:
        if psutil:
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            used_gb = mem.used / (1024**3)
            percent = mem.percent
            return percent, total_gb, used_gb
        return 0.0, 0.0, 0.0

    def get_network_kbps(self) -> Tuple[float, float]:
        if not psutil:
            return 0.0, 0.0
        now = time.time()
        net = psutil.net_io_counters()
        elapsed = now - self._prev_time
        if elapsed < 0.001:
            return 0.0, 0.0
        sent = (net.bytes_sent - self._prev_net.bytes_sent) / 1024 / elapsed
        recv = (net.bytes_recv - self._prev_net.bytes_recv) / 1024 / elapsed
        self._prev_net = net
        self._prev_time = now
        return sent, recv

    def get_processes(self) -> List[ProcessInfo]:
        if not psutil:
            return []
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                info = p.info
                mem_mb = info['memory_info'].rss / (1024 * 1024)
                procs.append(ProcessInfo(info['pid'], info['name'],
                                         info['cpu_percent'] or 0.0, mem_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return procs

    def kill_process(self, pid: int) -> bool:
        if not psutil:
            return False
        try:
            p = psutil.Process(pid)
            p.terminate()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False


class ScreenCapture:
    @staticmethod
    def capture() -> bytes:
        """Returns PNG bytes of screenshot or a small placeholder."""
        if mss:
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    screenshot = sct.grab(monitor)
                    from PIL import Image
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    return buf.getvalue()
            except Exception:
                pass
        if ImageGrab:
            try:
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                return buf.getvalue()
            except Exception:
                pass
        # Fallback: tiny placeholder
        from PIL import Image
        img = Image.new('RGB', (1, 1), color='red')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    @staticmethod
    def capture_base64() -> str:
        return base64.b64encode(ScreenCapture.capture()).decode('ascii')


# -------------------------------
# Communication protocol
# -------------------------------

def send_message(sock: socket.socket, msg: dict) -> None:
    data = json.dumps(msg).encode('utf-8')
    length = len(data)
    sock.sendall(struct.pack('!I', length) + data)


def recv_message(sock: socket.socket) -> dict:
    raw_len = recv_all(sock, 4)
    if not raw_len:
        return None
    length = struct.unpack('!I', raw_len)[0]
    data = recv_all(sock, length)
    return json.loads(data.decode('utf-8'))


def recv_all(sock: socket.socket, n: int) -> bytes:
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


# -------------------------------
# Agent class
# -------------------------------

class Agent:
    def __init__(self, controller_host: str, controller_port: int,
                 server_name: str, auth_key: str = 'nexus_default',
                 monitoring_interval: float = 2.0,
                 screen_interval: float = 5.0,
                 max_history: int = 100):
        self.controller_addr = (controller_host, controller_port)
        self.server_name = server_name
        self.auth_key = auth_key
        self.monitoring_interval = monitoring_interval
        self.screen_interval = screen_interval
        self.max_history = max_history
        self.sock: Optional[socket.socket] = None
        self.running = False
        self.monitor = SystemMonitor()
        self.history: deque = deque(maxlen=max_history)  # (MonitoringData)
        self.screen_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.command_thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self._connect()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.screen_thread = threading.Thread(target=self._screen_loop, daemon=True)
        self.screen_thread.start()
        self.command_thread = threading.Thread(target=self._command_listener, daemon=True)
        self.command_thread.start()
        # Main thread just waits
        while self.running:
            time.sleep(1)
        self.cleanup()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def cleanup(self):
        if self.sock:
            self.sock.close()
        print("[Agent] Stopped.")

    def _connect(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10)
                self.sock.connect(self.controller_addr)
                # Authenticate
                send_message(self.sock, {'type': 'auth', 'name': self.server_name, 'key': self.auth_key})
                resp = recv_message(self.sock)
                if resp and resp.get('type') == 'auth_ok':
                    print(f"[Agent] Connected to controller as {self.server_name}")
                    self.sock.settimeout(None)  # blocking for command listener
                    return
                else:
                    print("[Agent] Auth failed, retrying...")
                    self.sock.close()
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                print(f"[Agent] Connection failed: {e}, retrying in 5s")
                time.sleep(5)
            except Exception as e:
                print(f"[Agent] Error: {e}")
                time.sleep(5)

    def _monitor_loop(self):
        while self.running:
            try:
                cpu = self.monitor.get_cpu_percent()
                ram_pct, ram_total, ram_used = self.monitor.get_ram_info()
                net_sent, net_recv = self.monitor.get_network_kbps()
                data = MonitoringData(cpu, ram_pct, ram_total, ram_used, net_sent, net_recv)
                self.history.append(data)
                msg = {'type': 'metrics', 'data': data.to_dict()}
                if self.sock:
                    send_message(self.sock, msg)
            except (BrokenPipeError, ConnectionResetError, OSError):
                self._reconnect()
            except Exception as e:
                print(f"[Agent] Monitor error: {e}")
            time.sleep(self.monitoring_interval)

    def _screen_loop(self):
        while self.running:
            try:
                img_b64 = ScreenCapture.capture_base64()
                msg = {'type': 'screen', 'data': img_b64}
                if self.sock:
                    send_message(self.sock, msg)
            except Exception as e:
                print(f"[Agent] Screen error: {e}")
            time.sleep(self.screen_interval)

    def _command_listener(self):
        while self.running:
            if not self.sock:
                time.sleep(1)
                continue
            try:
                msg = recv_message(self.sock)
                if msg is None:
                    print("[Agent] Connection lost, reconnecting...")
                    self._reconnect()
                    continue
                self._handle_command(msg)
            except Exception as e:
                print(f"[Agent] Command error: {e}")

    def _handle_command(self, msg: dict):
        action = msg.get('action')
        if action == 'get_processes':
            procs = self.monitor.get_processes()
            reply = {'type': 'process_list', 'processes': [p.to_dict() for p in procs]}
            send_message(self.sock, reply)
        elif action == 'kill_process':
            pid = msg.get('pid')
            if pid is not None:
                success = self.monitor.kill_process(int(pid))
                reply = {'type': 'kill_result', 'pid': pid, 'success': success}
                send_message(self.sock, reply)
        elif action == 'get_history':
            hist = [d.to_dict() for d in self.history]
            reply = {'type': 'history', 'data': hist}
            send_message(self.sock, reply)
        # else ignore

    def _reconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        while self.running:
            try:
                self._connect()
                return
            except Exception:
                time.sleep(5)


# -------------------------------
# Controller side
# -------------------------------

class ConnectedAgent:
    def __init__(self, name: str, sock: socket.socket):
        self.name = name
        self.sock = sock
        self.last_metrics: Optional[MonitoringData] = None
        self.last_screen: Optional[str] = None  # base64
        self.processes: List[ProcessInfo] = []
        self.status: str = 'online'
        self.history: List[MonitoringData] = []  # will store recent metrics from this agent
        self._lock = threading.Lock()

    def update_metrics(self, data: MonitoringData):
        self.last_metrics = data
        self.history.append(data)
        # limit history size
        if len(self.history) > 200:
            self.history = self.history[-200:]

    def set_screen(self, img_b64: str):
        self.last_screen = img_b64

    def set_processes(self, procs: List[ProcessInfo]):
        self.processes = procs

    def send_command(self, cmd: dict):
        send_message(self.sock, cmd)

    def close(self):
        try:
            self.sock.close()
        except:
            pass


class NexusCtrl:
    def __init__(self, host: str = '0.0.0.0', port: int = 9999):
        self.host = host
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.agents: Dict[str, ConnectedAgent] = {}
        self.tasks: List[Task] = []
        self.running = False
        self._agent_lock = threading.Lock()

    def start(self):
        self.running = True
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        server_thread.start()
        print(f"[NexusCtrl] Listening on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        for agent in self.agents.values():
            agent.close()
        if self.server_sock:
            self.server_sock.close()

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
                threading.Thread(target=self._handle_new_connection, args=(client_sock, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Accept error: {e}")

    def _handle_new_connection(self, sock: socket.socket, addr):
        try:
            # Wait for auth
            msg = recv_message(sock)
            if not msg or msg.get('type') != 'auth':
                sock.close()
                return
            name = msg.get('name', f'unknown-{addr[1]}')
            key = msg.get('key')
            # Simple auth check
            if key != 'nexus_default':
                send_message(sock, {'type': 'auth_fail'})
                sock.close()
                return
            send_message(sock, {'type': 'auth_ok'})
            agent = ConnectedAgent(name, sock)
            with self._agent_lock:
                self.agents[name] = agent
            print(f"[NexusCtrl] Agent '{name}' connected from {addr}")
            # Handle incoming messages from this agent
            while self.running:
                try:
                    msg = recv_message(sock)
                    if msg is None:
                        break
                    self._process_agent_msg(name, msg)
                except Exception as e:
                    break
        except Exception:
            pass
        finally:
            # Agent disconnected
            with self._agent_lock:
                if name in self.agents:
                    del self.agents[name]
            print(f"[NexusCtrl] Agent '{name}' disconnected")
            sock.close()

    def _process_agent_msg(self, agent_name: str, msg: dict):
        agent = self.agents.get(agent_name)
        if not agent:
            return
        msg_type = msg.get('type')
        if msg_type == 'metrics':
            data = MonitoringData.from_dict(msg['data'])
            agent.update_metrics(data)
        elif msg_type == 'screen':
            agent.set_screen(msg.get('data', ''))
        elif msg_type == 'process_list':
            procs = [ProcessInfo.from_dict(p) for p in msg['processes']]
            agent.set_processes(procs)
        elif msg_type == 'kill_result':
            # Could log or notify user
            pass
        elif msg_type == 'history':
            hist = [MonitoringData.from_dict(h) for h in msg['data']]
            agent.history = hist
        # other types ignored

    # ---------- Public API / CLI methods ----------

    def list_agents(self) -> List[str]:
        with self._agent_lock:
            return list(self.agents.keys())

    def get_agent_info(self, name: str) -> Optional[dict]:
        agent = self.agents.get(name)
        if not agent:
            return None
        metrics = agent.last_metrics
        return {
            'name': agent.name,
            'status': agent.status,
            'cpu': metrics.cpu_percent if metrics else None,
            'ram_percent': metrics.ram_percent if metrics else None,
            'ram_total_gb': metrics.ram_total_gb if metrics else None,
            'ram_used_gb': metrics.ram_used_gb if metrics else None,
            'network_sent': metrics.network_sent_kbps if metrics else None,
            'network_recv': metrics.network_recv_kbps if metrics else None,
            'process_count': len(agent.processes),
            'last_update': metrics.timestamp if metrics else None,
        }

    def get_agent_processes(self, name: str) -> List[ProcessInfo]:
        agent = self.agents.get(name)
        if agent:
            return agent.processes
        return []

    def refresh_processes(self, name: str):
        agent = self.agents.get(name)
        if agent:
            agent.send_command({'action': 'get_processes'})

    def kill_process(self, agent_name: str, pid: int) -> bool:
        agent = self.agents.get(agent_name)
        if agent:
            agent.send_command({'action': 'kill_process', 'pid': pid})
            return True
        return False

    def request_history(self, agent_name: str):
        agent = self.agents.get(agent_name)
        if agent:
            agent.send_command({'action': 'get_history'})

    # Task management
    def add_task(self, title: str, description: str = "", priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
        task = Task(title, description, priority)
        self.tasks.append(task)
        return task

    def complete_task(self, index: int) -> bool:
        if 0 <= index < len(self.tasks):
            self.tasks[index].completed = True
            return True
        return False

    def list_tasks(self, filter_completed: Optional[bool] = None) -> List[Task]:
        if filter_completed is None:
            return self.tasks
        return [t for t in self.tasks if t.completed == filter_completed]

    def remove_task(self, index: int) -> bool:
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            return True
        return False


# -------------------------------
# Command-line interface
# -------------------------------

class CLI:
    def __init__(self, nexus: NexusCtrl):
        self.nexus = nexus

    def run(self):
        print("NexusCtrl CLI - Type 'help' for commands")
        while True:
            try:
                cmd = input(">> ").strip().split()
                if not cmd:
                    continue
                self.execute(cmd)
            except KeyboardInterrupt:
                print("\nExiting...")
                self.nexus.stop()
                break
            except Exception as e:
                print(f"Error: {e}")

    def execute(self, args):
        cmd = args[0].lower()
        if cmd == 'help':
            self.help()
        elif cmd == 'agents':
            self.show_agents()
        elif cmd == 'info':
            self.show_agent_info(args)
        elif cmd == 'procs':
            self.show_processes(args)
        elif cmd == 'kill':
            self.kill_process_cmd(args)
        elif cmd == 'refresh':
            self.refresh_procs(args)
        elif cmd == 'tasks':
            self.show_tasks(args)
        elif cmd == 'addtask':
            self.add_task_cmd(args)
        elif cmd == 'comptask':
            self.complete_task_cmd(args)
        elif cmd == 'deltask':
            self.remove_task_cmd(args)
        elif cmd == 'exit' or cmd == 'quit':
            self.nexus.stop()
            sys.exit(0)
        else:
            print(f"Unknown command: {cmd}. Type 'help'.")

    def help(self):
        print("""
Commands:
  agents                 - list connected agents
  info <agent_name>      - show agent monitoring info
  procs <agent_name>     - show cached processes (use 'refresh' to update)
  refresh <agent_name>   - request fresh process list from agent
  kill <agent_name> <pid>- kill a process on an agent
  tasks [all|pending|done] - list tasks (default all)
  addtask <priority> "<title>" "<description>" - add task (priority: low/medium/high/critical)
  comptask <index>       - mark task as completed by its index in list
  deltask <index>        - delete task by index
  exit                   - quit
""")

    def show_agents(self):
        agents = self.nexus.list_agents()
        if agents:
            print("Connected agents:")
            for a in agents:
                print(f"  - {a}")
        else:
            print("No agents connected.")

    def show_agent_info(self, args):
        if len(args) < 2:
            print("Usage: info <agent_name>")
            return
        name = args[1]
        info = self.nexus.get_agent_info(name)
        if info:
            print(f"\nAgent: {info['name']} [{info['status']}]")
            if info['cpu'] is not None:
                print(f"  CPU: {info['cpu']:.1f}%")
            if info['ram_percent'] is not None:
                print(f"  RAM: {info['ram_percent']:.1f}% ({info['ram_used_gb']:.1f}/{info['ram_total_gb']:.1f} GB)")
            if info['network_sent'] is not None:
                print(f"  Net Sent: {info['network_sent']:.1f} kbps, Recv: {info['network_recv']:.1f} kbps")
            print(f"  Cached processes: {info['process_count']}")
            print(f"  Last update: {time.ctime(info['last_update']) if info['last_update'] else 'never'}")
        else:
            print(f"Agent '{name}' not found.")

    def show_processes(self, args):
        if len(args) < 2:
            print("Usage: procs <agent_name>")
            return
        name = args[1]
        procs = self.nexus.get_agent_processes(name)
        if procs:
            print(f"Processes on {name}:")
            for p in procs:
                print(f"  PID:{p.pid} {p.name} CPU:{p.cpu_percent:.1f}% MEM:{p.memory_mb:.1f}MB")
        else:
            print(f"No cached processes for '{name}'. Use 'refresh {name}'.")

    def refresh_procs(self, args):
        if len(args) < 2:
            print("Usage: refresh <agent_name>")
            return
        name = args[1]
        if name not in self.nexus.list_agents():
            print(f"Agent '{name}' not connected.")
            return
        self.nexus.refresh_processes(name)
        print(f"Sent process list request to '{name}'. Wait a moment, then 'procs {name}'.")

    def kill_process_cmd(self, args):
        if len(args) < 3:
            print("Usage: kill <agent_name> <pid>")
            return
        name, pid_str = args[1], args[2]
        try:
            pid = int(pid_str)
        except ValueError:
            print("PID must be integer.")
            return
        if name not in self.nexus.list_agents():
            print(f"Agent '{name}' not connected.")
            return
        self.nexus.kill_process(name, pid)
        print(f"Sent kill command for PID {pid} to '{name}'.")

    def show_tasks(self, args):
        filter_str = args[1] if len(args) > 1 else 'all'
        if filter_str == 'all':
            tasks = self.nexus.list_tasks()
        elif filter_str == 'pending':
            tasks = self.nexus.list_tasks(filter_completed=False)
        elif filter_str == 'done':
            tasks = self.nexus.list_tasks(filter_completed=True)
        else:
            print("Invalid filter. Use: all, pending, done")
            return
        if tasks:
            for idx, t in enumerate(tasks):
                status = 'X' if t.completed else ' '
                print(f"[{status}] {idx}: [{t.priority.name}] {t.title} - {t.description}")
        else:
            print("No tasks.")

    def add_task_cmd(self, args):
        if len(args) < 4:
            print("Usage: addtask <priority> \"<title>\" \"<description>\"")
            return
        priority_str = args[1].lower()
        priority_map = {'low': TaskPriority.LOW, 'medium': TaskPriority.MEDIUM,
                        'high': TaskPriority.HIGH, 'critical': TaskPriority.CRITICAL}
        if priority_str not in priority_map:
            print("Invalid priority. Use: low, medium, high, critical")
            return
        # Simple arg parsing: join remaining items into one string and split by quotes?
        # Let's just take rest of line after priority and split by quotes
        rest = ' '.join(args[2:])
        import re
        parts = re.findall(r'"([^"]*)"', rest)
        if len(parts) < 2:
            print("Title and description must be in quotes.")
            return
        title, description = parts[0], parts[1]
        task = self.nexus.add_task(title, description, priority_map[priority_str])
        print(f"Task added: [{task.priority.name}] {task.title}")

    def complete_task_cmd(self, args):
        if len(args) < 2:
            print("Usage: comptask <index>")
            return
        try:
            idx = int(args[1])
        except ValueError:
            print("Index must be integer.")
            return
        if self.nexus.complete_task(idx):
            print(f"Task {idx} marked as completed.")
        else:
            print("Invalid index.")

    def remove_task_cmd(self, args):
        if len(args) < 2:
            print("Usage: deltask <index>")
            return
        try:
            idx = int(args[1])
        except ValueError:
            print("Index must be integer.")
            return
        if self.nexus.remove_task(idx):
            print(f"Task {idx} removed.")
        else:
            print("Invalid index.")


# -------------------------------
# Main entry points
# -------------------------------

def main_controller():
    nexus = NexusCtrl()
    nexus.start()
    cli = CLI(nexus)
    cli.run()


def main_agent():
    import argparse
    parser = argparse.ArgumentParser(description='NexusCtrl Agent')
    parser.add_argument('--host', default='127.0.0.1', help='Controller host')
    parser.add_argument('--port', default=9999, type=int, help='Controller port')
    parser.add_argument('--name', default=socket.gethostname(), help='Agent name')
    parser.add_argument('--key', default='nexus_default', help='Auth key')
    args = parser.parse_args()
    agent = Agent(args.host, args.port, args.name, args.key)
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'agent':
        sys.argv.pop(1)
        main_agent()
    else:
        main_controller()