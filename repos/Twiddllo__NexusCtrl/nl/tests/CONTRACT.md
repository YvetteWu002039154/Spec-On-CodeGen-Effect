# Behavioral contract — `NexusCtrl` **NL track**

## Description feature → origin grounding

| Description feature | Origin evidence | Scored |
|---|---|---|
| Performance history usage | `app.py::MetricSnapshot` table (a series per server) | **N1** |
| Collects system metrics (CPU, RAM, network) | `agent.py::collect_metrics` → `{cpu, ram, net_rx, net_tx}` | **N2** |
| Active process monitoring / view active processes | `agent.py::get_processes` (psutil `process_iter`) | **N3** |
| Runs as a background service | `agent.py` agent serve/command loop | **N4** |
| Terminate processes remotely (kill) | `agent.py` action `"kill"` → `psutil.Process(pid).terminate()` | **N5** |
| Create and manage tasks | `app.py::Task` + `POST /tasks` | **N6**, **N7** |
| Set priorities (critical/high/medium/low) | `app.py::TaskPriority` = `{low, medium, high, critical}` | **N8** |
| Track task completion status | `app.py::TaskStatus` (`done` is the terminal/complete stage) | **N9** |
| Monitor server status (online/offline) | `app.py::ServerStatus` = `{online, offline, warning, maintenance}` | **N10** |

## Behaviors pinned

### Server Monitoring
- **N1. Performance history.** Repeated metric samples are **retained as a
  series**.

### Agent Capabilities (the remote target machine)
- **N2. Metrics collection.** The agent **self-collects** a metrics
  record that exposes **CPU**, **RAM**, and **network** dimensions, and whose **RAM% matches the live host**. A fed or hardcoded record fails.
- **N3. View active processes.** The agent enumerates the **real** host processes — the running test's own PID must appear. A simulated agent (mock or empty list) fails.
- **N4. Runs as a background service.** The agent exposes a `start()` service entry point.
- **N5. Responds to remote kill.** The agent exposes a kill command and, for a nonexistent PID, reports failure (no real process is touched).

### Task Management (the controller / local machine)
- **N6. Create task.** A task can be created and then observed to exist.
- **N7. Manage multiple tasks.** Several tasks can be created and all are tracked.
- **N8. Priority vocabulary.** The task-priority vocabulary contains
  `critical`, `high`, `medium`, and `low`.
- **N9. Completion tracking.** A created task can be marked complete and then
  observed in a completed/done state.

### Server Control (the controller / local machine)
- **N10. Status vocabulary.** The server-status vocabulary contains both
  `online` and `offline`.
