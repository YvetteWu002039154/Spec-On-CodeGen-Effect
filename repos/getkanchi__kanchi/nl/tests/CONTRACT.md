# Behavioral contract — `Kanchi` **NL track**

## Description feature → origin grounding

| Description feature | Origin evidence |
|---|---|
| "insights into task execution" (states) | `monitor.py` maps Celery task events (`task-succeeded`/`task-failed`/`task-retried`/…); `database.TaskDailyStatsDB` columns `{succeeded, failed, retried, revoked, pending}` |
| "Task retry tracking" | `database.TaskEventDB.retry_count` / `.retries`; `database.RetryRelationshipDB` |
| "orphan detection" | `database.TaskEventDB.is_orphan` / `.orphaned_at`; `TaskLatestDB.is_orphan` |
| "Daily task statistics and history" | `database.TaskDailyStatsDB` (`succeeded`, `failed`, `retried`, `revoked`, `total_executions`, …) |
| "Worker health monitoring" | `database.WorkerEventDB` (`status`, `active_tasks`, `timestamp`); `monitor.get_workers_info` keeps a per-host `{status, timestamp}` map |
| "Real-time task monitoring via WebSocket" | `connection_manager.ConnectionManager` — `active_connections: list`, `disconnect(ws)` removes the ws from every per-client store and is idempotent |
| "Auto-migrations with Alembic" | `database.DatabaseManager.run_migrations()` (runs Alembic `upgrade head`) |

## Behaviors pinned

### Task execution insights
- **N1. Task-state vocabulary.** The system's task-state vocabulary includes a
  **success**, a **failure**, and a **retry** state (grounded in the Celery
  event set and `TaskDailyStatsDB`'s outcome columns).
- **N2. Retry counter.** A task record exposes a **retry counter**
  (`retries` / `retry_count`).
- **N3. Orphan detection.** An **orphan-detection** surface exists — a task
  record's orphan flag/method, or a dedicated detector.

### Daily statistics
- **N4. Daily-statistics counts.** A daily-statistics structure exposes both a
  **succeeded** and a **failed** count.
- **N5. Statistics accumulation.** Recording a **success** outcome into a
  daily-statistics record **increments its success counter** (a behavioral
  drive, not mere field presence).

### Worker health monitoring
- **N6. Worker health.** A worker record exposes a **health/status** field and a
  **heartbeat** timestamp.

### Real-time WebSocket registry
- **N7. Disconnect is idempotent.** A connection registry's `disconnect`
  **removes a registered connection** and is **idempotent** — disconnecting an
  unknown/already-removed connection does not raise.

### Auto-migrations
- **N8. Migration runner.** An **auto-migration** runner capability is exposed
  (a migration manager / `run_migrations`-style entry point).

## Dependency usage

> "real-time Celery task monitoring ... Auto-migrations with Alembic."

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `celery` | FAIL | FAIL | pass | pass |
| D2 | imports and uses `alembic` | FAIL | FAIL | FAIL | pass |
