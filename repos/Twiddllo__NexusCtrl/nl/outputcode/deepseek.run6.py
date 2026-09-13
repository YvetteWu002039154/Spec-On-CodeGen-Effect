import socket
import threading
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import sys
import os
import base64
from io import BytesIO

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: Priority = Priority.MEDIUM
    completed: bool = False
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def mark_completed(self):
        self.completed = True
        self.completed_at = time.time()


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def add_task(self, name: str, description: str, priority: Priority) -> Task:
        task = Task(name=name, description=description, priority=priority)
        self.tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def list_tasks(self, include_completed: bool = True) -> List[Task]:
        tasks = list(self.tasks.values())
        if not include_completed:
            tasks = [t for t in tasks if not t.completed]
        return tasks

    def mark_task_completed(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if task:
            task.mark_completed()
            return True
        return False

    def remove_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False


class Server:
    def __init__(self, agent_id: str, client_socket: socket.socket):
        self.agent_id = agent_id
        self.socket = client_socket
        self.status = "online"
        self.cpu_usage: float = 0.0
        self.ram_used: float = 0.0
        self.ram_total: float = 0.0
        self.network_sent: float = 0.0
        self.network_recv: float = 0.0
        self.processes: List[Dict[str, Any]] = []
        self.last_screen: Optional[str] = None  # base64 encoded image
        self.history: List[Dict[str, Any]] = []
        self.max_history = 50
        self.lock = threading.Lock()
        self._running = True
        self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self.receiver_thread.start()

    def update_metrics(self, data: Dict[str, Any]):
        with self.lock:
            self.cpu_usage = data.get("cpu", 0.0)
            self.ram_used = data.get("ram_used", 0.0)
            self.ram_total = data.get("ram_total", 0.0)
            self.network_sent = data.get("network_sent", 0.0)
            self.network_recv = data.get("network_recv", 0.0)
            self.processes = data.get("processes", [])
            self.status = "online"
            # record history
            self.history.append({
                "timestamp": time.time(),
                "cpu": self.cpu_usage,
                "ram_used": self.ram_used,
                "ram_total": self.ram_total,
                "network_sent": self.network_sent,
                "network_recv": self.network_recv
            })
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

    def set_screen(self, image_base64: str):
        with self.lock:
            self.last_screen = image_base64

    def get_processes(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.processes)

    def kill_process(self, pid: int) -> None:
        self._send_command({"type": "command", "command": "kill_process", "pid": pid})

    def capture_screen(self) -> None:
        self._send_command({"type": "command", "command": "capture_screen"})

    def _send_command(self, command: Dict[str, Any]) -> None:
        try:
            message = json.dumps(command) + "\n"
            self.socket.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending command to {self.agent_id}: {e}")

    def _receiver_loop(self):
        buffer = b""
        while self._running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self._process_message(line.decode('utf-8'))
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"Receiver error for {self.agent_id}: {e}")
                break
        self.status = "offline"
        self._running = False

    def _process_message(self, message_str: str):
        try:
            msg = json.loads(message_str)
            msg_type = msg.get("type")
            if msg_type == "metrics":
                self.update_metrics(msg.get("data", {}))
            elif msg_type == "screen":
                self.set_screen(msg.get("data", ""))
        except json.JSONDecodeError:
            pass  # ignore malformed JSON

    def close(self):
        self._running = False
        try:
            self.socket.close()
        except:
            pass


class Agent:
    def __init__(self, controller_host: str = "localhost", controller_port: int = 9999):
        self.controller_host = controller_host
        self.controller_port = controller_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.send_interval = 2.0  # seconds

    def start(self):
        self.socket.connect((self.controller_host, self.controller_port))
        print(f"Agent connected to controller at {self.controller_host}:{self.controller_port}")
        # Start sender thread
        sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        sender_thread.start()
        # Receiver loop in main thread
        self._receiver_loop()

    def _sender_loop(self):
        while self.running:
            metrics = self._collect_metrics()
            msg = json.dumps({"type": "metrics", "data": metrics}) + "\n"
            try:
                self.socket.sendall(msg.encode('utf-8'))
            except Exception as e:
                print(f"Failed to send metrics: {e}")
                self.running = False
                break
            time.sleep(self.send_interval)

    def _receiver_loop(self):
        buffer = b""
        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self._handle_command(line.decode('utf-8'))
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"Receiver error: {e}")
                break
        self.running = False
        self.socket.close()
        print("Agent disconnected.")

    def _handle_command(self, command_str: str):
        try:
            msg = json.loads(command_str)
            if msg.get("type") != "command":
                return
            cmd = msg.get("command")
            if cmd == "kill_process":
                pid = msg.get("pid")
                if pid is not None:
                    self._kill_process(pid)
            elif cmd == "capture_screen":
                self._capture_and_send_screen()
        except json.JSONDecodeError:
            pass

    def _collect_metrics(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {
                "cpu": 0.0,
                "ram_used": 0.0,
                "ram_total": 0.0,
                "network_sent": 0.0,
                "network_recv": 0.0,
                "processes": []
            }
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        ram_used = mem.used / (1024 * 1024 * 1024)  # GB
        ram_total = mem.total / (1024 * 1024 * 1024)  # GB
        net = psutil.net_io_counters()
        network_sent = net.bytes_sent
        network_recv = net.bytes_recv
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent'],
                    "memory_bytes": info['memory_info'].rss if info['memory_info'] else 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {
            "cpu": cpu,
            "ram_used": ram_used,
            "ram_total": ram_total,
            "network_sent": network_sent,
            "network_recv": network_recv,
            "processes": processes
        }

    def _kill_process(self, pid: int):
        if PSUTIL_AVAILABLE:
            try:
                p = psutil.Process(pid)
                p.terminate()
                print(f"Process {pid} terminated.")
            except psutil.NoSuchProcess:
                print(f"No process with PID {pid}.")
            except Exception as e:
                print(f"Failed to kill process {pid}: {e}")
        else:
            print("psutil not available, cannot kill process.")

    def _capture_and_send_screen(self):
        if not PIL_AVAILABLE:
            print("PIL not available, cannot capture screen.")
            return
        try:
            img = ImageGrab.grab()
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            msg = json.dumps({"type": "screen", "data": img_str}) + "\n"
            self.socket.sendall(msg.encode('utf-8'))
            print("Screen captured and sent.")
        except Exception as e:
            print(f"Screen capture failed: {e}")


class NexusCtrl:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.servers: Dict[str, Server] = {}
        self.task_manager = TaskManager()
        self._running = True
        self._server_socket: Optional[socket.socket] = None

    def start(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        print(f"NexusCtrl controller listening on {self.host}:{self.port}")
        # Accept connections in a separate thread
        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        accept_thread.start()
        # CLI main thread
        self._cli_loop()

    def _accept_loop(self):
        while self._running:
            try:
                client_sock, addr = self._server_socket.accept()
                print(f"New agent connected from {addr}")
                agent_id = f"{addr[0]}:{addr[1]}_{int(time.time())}"
                server = Server(agent_id, client_sock)
                self.servers[agent_id] = server
            except socket.error as e:
                if self._running:
                    print(f"Accept error: {e}")
                break

    def _cli_loop(self):
        print("\nNexusCtrl CLI. Type 'help' for commands.")
        while self._running:
            try:
                cmd_input = input("nexus> ").strip()
                if not cmd_input:
                    continue
                self._handle_command(cmd_input)
            except KeyboardInterrupt:
                print("\nShutting down...")
                self._running = False
                break
            except EOFError:
                break

    def _handle_command(self, cmd: str):
        parts = cmd.split()
        if not parts:
            return
        base_cmd = parts[0].lower()

        if base_cmd == "help":
            self._print_help()
        elif base_cmd == "servers":
            self._list_servers()
        elif base_cmd == "server":
            if len(parts) < 2:
                print("Usage: server <agent_id>")
                return
            self._server_detail(parts[1])
        elif base_cmd == "processes":
            if len(parts) < 2:
                print("Usage: processes <agent_id>")
                return
            self._list_processes(parts[1])
        elif base_cmd == "kill":
            if len(parts) < 3:
                print("Usage: kill <agent_id> <pid>")
                return
            try:
                pid = int(parts[2])
            except ValueError:
                print("PID must be a number.")
                return
            self._kill_process(parts[1], pid)
        elif base_cmd == "capture":
            if len(parts) < 2:
                print("Usage: capture <agent_id>")
                return
            self._capture_screen(parts[1])
        elif base_cmd == "screen":
            if len(parts) < 2:
                print("Usage: screen <agent_id>")
                return
            self._show_screen(parts[1])
        elif base_cmd == "tasks":
            self._list_tasks()
        elif base_cmd == "addtask":
            self._add_task(parts)
        elif base_cmd == "completetask":
            if len(parts) < 2:
                print("Usage: completetask <task_id>")
                return
            self._complete_task(parts[1])
        elif base_cmd == "removetask":
            if len(parts) < 2:
                print("Usage: removetask <task_id>")
                return
            self._remove_task(parts[1])
        elif base_cmd == "exit":
            self._running = False
            print("Exiting.")
        else:
            print("Unknown command. Type 'help' for list.")

    def _print_help(self):
        print("""
Available commands:
  servers                 - List all connected servers
  server <agent_id>       - Show details for a server
  processes <agent_id>    - List processes on a server
  kill <agent_id> <pid>   - Kill a process on a server
  capture <agent_id>      - Capture screen from agent
  screen <agent_id>       - Display last screen capture base64 (first 100 chars)
  tasks                   - List all tasks
  addtask <name> <desc> <priority> - Add a new task (priority: CRITICAL/HIGH/MEDIUM/LOW)
  completetask <task_id>  - Mark task as completed
  removetask <task_id>    - Remove a task
  help                    - Show this help
  exit                    - Shutdown controller
""")

    def _list_servers(self):
        if not self.servers:
            print("No servers connected.")
            return
        for agent_id, server in self.servers.items():
            status = server.status
            print(f"{agent_id} - Status: {status}, CPU: {server.cpu_usage:.1f}%, RAM: {server.ram_used:.2f}/{server.ram_total:.2f} GB")

    def _server_detail(self, agent_id: str):
        server = self.servers.get(agent_id)
        if not server:
            print("Server not found.")
            return
        print(f"Agent ID: {server.agent_id}")
        print(f"Status: {server.status}")
        print(f"CPU: {server.cpu_usage:.1f}%")
        print(f"RAM: {server.ram_used:.2f}/{server.ram_total:.2f} GB")
        print(f"Network Sent: {server.network_sent} bytes")
        print(f"Network Recv: {server.network_recv} bytes")
        print(f"History entries: {len(server.history)}")

    def _list_processes(self, agent_id: str):
        server = self.servers.get(agent_id)
        if not server:
            print("Server not found.")
            return
        processes = server.get_processes()
        if not processes:
            print("No process data available.")
            return
        print(f"Processes on {agent_id}:")
        for proc in processes[:20]:  # limit output
            print(f"  PID {proc['pid']}: {proc['name']} (CPU: {proc['cpu_percent']:.1f}%, Mem: {proc['memory_bytes']/1024:.1f} KB)")

    def _kill_process(self, agent_id: str, pid: int):
        server = self.servers.get(agent_id)
        if not server:
            print("Server not found.")
            return
        server.kill_process(pid)
        print(f"Kill command sent for PID {pid} on {agent_id}")

    def _capture_screen(self, agent_id: str):
        server = self.servers.get(agent_id)
        if not server:
            print("Server not found.")
            return
        server.capture_screen()
        print("Screen capture request sent.")

    def _show_screen(self, agent_id: str):
        server = self.servers.get(agent_id)
        if not server:
            print("Server not found.")
            return
        screen = server.last_screen
        if screen:
            # For demonstration we print first 100 characters
            print(f"Base64 image data (first 100 chars): {screen[:100]}...")
        else:
            print("No screen capture available. Use 'capture <agent_id>' first.")

    def _list_tasks(self):
        tasks = self.task_manager.list_tasks()
        if not tasks:
            print("No tasks.")
            return
        for task in tasks:
            status = "Done" if task.completed else "Pending"
            print(f"{task.task_id} - {task.name} [{task.priority.value}] - {status}")

    def _add_task(self, parts: List[str]):
        if len(parts) < 4:
            print("Usage: addtask <name> <description> <priority>")
            return
        name = parts[1]
        desc = parts[2]
        prio_str = parts[3].upper()
        try:
            priority = Priority(prio_str.lower())
        except ValueError:
            print("Invalid priority. Use CRITICAL/HIGH/MEDIUM/LOW.")
            return
        task = self.task_manager.add_task(name, desc, priority)
        print(f"Task added: {task.task_id}")

    def _complete_task(self, task_id: str):
        if self.task_manager.mark_task_completed(task_id):
            print("Task marked completed.")
        else:
            print("Task not found.")

    def _remove_task(self, task_id: str):
        if self.task_manager.remove_task(task_id):
            print("Task removed.")
        else:
            print("Task not found.")

    def shutdown(self):
        self._running = False
        for server in self.servers.values():
            server.close()
        if self._server_socket:
            self._server_socket.close()
        print("NexusCtrl shut down.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="NexusCtrl - Personal RDP Server Management Tool")
    parser.add_argument("--mode", choices=["controller", "agent"], required=True, help="Run as controller or agent")
    parser.add_argument("--host", default="localhost", help="Host for controller or agent connection (default localhost)")
    parser.add_argument("--port", type=int, default=9999, help="Port for controller/agent (default 9999)")
    args = parser.parse_args()

    if args.mode == "controller":
        ctrl = NexusCtrl(args.host, args.port)
        try:
            ctrl.start()
        except KeyboardInterrupt:
            ctrl.shutdown()
    elif args.mode == "agent":
        agent = Agent(args.host, args.port)
        try:
            agent.start()
        except KeyboardInterrupt:
            agent.running = False
            print("Agent stopping.")


if __name__ == "__main__":
    main()