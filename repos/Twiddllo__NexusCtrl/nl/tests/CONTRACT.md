# Behavioral contract — `NexusCtrl` **NL track**

## Description features

| Description feature | Scored |
|---|---|
| Performance history usage | **N1** |
| Collects system metrics (CPU, RAM, network) | **N2** |
| Active process monitoring / view active processes | **N3** |
| Runs as a background service | **N4** |
| Terminate processes remotely (kill) | **N5** |
| Create and manage tasks | **N6**, **N7** |
| Set priorities (critical/high/medium/low) | **N8** |
| Track task completion status | **N9** |
| Monitor server status (online/offline) | **N10** |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Server Monitoring | **Performance history.** Repeated metric samples are **retained as a series**. |
| N2 | Agent Capabilities (the remote target machine) | **Metrics collection.** The agent **self-collects** a metrics record that exposes **CPU**, **RAM**, and **network** dimensions, and whose **RAM% matches the live host**. A fed or hardcoded record fails. |
| N3 | Agent Capabilities (the remote target machine) | **View active processes.** The agent enumerates the **real** host processes — the running test's own PID must appear. A simulated agent (mock or empty list) fails. |
| N4 | Agent Capabilities (the remote target machine) | **Runs as a background service.** The agent exposes a `start()` service entry point. |
| N5 | Agent Capabilities (the remote target machine) | **Responds to remote kill.** The agent exposes a kill command and, for a nonexistent PID, reports failure (no real process is touched). |
| N6 | Task Management (the controller / local machine) | **Create task.** A task can be created and then observed to exist. |
| N7 | Task Management (the controller / local machine) | **Manage multiple tasks.** Several tasks can be created and all are tracked. |
| N8 | Task Management (the controller / local machine) | **Priority vocabulary.** The task-priority vocabulary contains `critical`, `high`, `medium`, and `low`. |
| N9 | Task Management (the controller / local machine) | **Completion tracking.** A created task can be marked complete and then observed in a completed/done state. |
| N10 | Server Control (the controller / local machine) | **Status vocabulary.** The server-status vocabulary contains both `online` and `offline`. |

