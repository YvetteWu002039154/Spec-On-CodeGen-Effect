# Behavioral contract — `Kanchi` **NL track**

## Description features

| Description feature |
|---|
| "insights into task execution" (states) |
| "Task retry tracking" |
| "orphan detection" |
| "Daily task statistics and history" |
| "Worker health monitoring" |
| "Real-time task monitoring via WebSocket" |
| "Auto-migrations with Alembic" |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Task execution insights | **Task-state vocabulary.** The system's task-state vocabulary includes a **success**, a **failure**, and a **retry** state (grounded in the Celery event set and `TaskDailyStatsDB`'s outcome columns). |
| N2 | Task execution insights | **Retry counter.** A task record exposes a **retry counter** (`retries` / `retry_count`). |
| N3 | Task execution insights | **Orphan detection.** An **orphan-detection** surface exists — a task record's orphan flag/method, or a dedicated detector. |
| N4 | Daily statistics | **Daily-statistics counts.** A daily-statistics structure exposes both a **succeeded** and a **failed** count. |
| N5 | Daily statistics | **Statistics accumulation.** Recording a **success** outcome into a daily-statistics record **increments its success counter** (a behavioral drive, not mere field presence). |
| N6 | Worker health monitoring | **Worker health.** A worker record exposes a **health/status** field and a **heartbeat** timestamp. |
| N7 | Real-time WebSocket registry | **Disconnect is idempotent.** A connection registry's `disconnect` **removes a registered connection** and is **idempotent** — disconnecting an unknown/already-removed connection does not raise. |
| N8 | Auto-migrations | **Migration runner.** An **auto-migration** runner capability is exposed (a migration manager / `run_migrations`-style entry point). |

## Dependency usage

> "real-time Celery task monitoring ... Auto-migrations with Alembic."

| # | Check |
|---|---|
| D1 | imports and uses `celery` |
| D2 | imports and uses `alembic` |
