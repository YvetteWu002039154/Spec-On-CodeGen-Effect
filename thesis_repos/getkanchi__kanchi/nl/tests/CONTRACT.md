# Behavioral contract — `Kanchi` **NL track**

Reference: origin repo `kanchi-main/agent/` 
- the Celery-event agent (`monitor.py`, `connection_manager.py`, `event_handler.py`,
`database.py`, `services/actions/…`).
- `nl/input/description.txt`

Behavior is asserted on **observable capability/effect**:
- an in-memory dataclass core
- a SQLite repository stack with an `EventBus`
- two SQLAlchemy + FastAPI services

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

## Harness

Behavior is asserted on **observable capability/effect** across an in-memory
dataclass core, a SQLite repository stack with an `EventBus`, and two SQLAlchemy +
FastAPI services. Each generation is driven by its own explicit driver
(`adapter.py`) that names the concrete classes and methods and translates the
contract behavior into that generation's own vocabulary — `disconnect` vs
`remove_connection`, an enum vs string states, a wide vs long stats schema, a sync
vs `async` method. A behavior a generation genuinely does not implement FAILS
naturally; the driver must reach whatever surface *does* implement it.

## Portability

The loader keeps every third-party dependency **real** (no stubbing) and each
module imports cleanly. Behaviors are exercised without a live broker or HTTP
server: field/enum reads, an in-memory connection registry, gpt's throwaway local
SQLite `Database`, a real in-memory SQLAlchemy session for gemini's stats service,
and a minimal seeded async session that runs deepseek's async `update_daily_stats`
increment without an aiosqlite engine.

## Dependency usage
The behaviors above are deliberately **dependency-agnostic** (the drivers
fake or stub external services), so a generation that reimplements a
dependency with a plain substitute still passes them. This section pins the
complementary axis — does a generation **import and use the package(s) the
description names**, rather than hand-roll a substitute?

> "real-time Celery task monitoring ... Auto-migrations with Alembic."

The check is **static** (`loader.dependency_used`, AST only — it never
imports the module, so it is independent of whether the package is installed).
A dependency passes when the file both **imports** the package *and*
**references** what it imported at least once (guarding against a dead
import). It is deliberately scoped to import-and-use, not correct-API
verification. A generation delivered as a full project directory passes if
any of its `.py` files imports-and-uses the package.

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `celery` | FAIL | FAIL | pass | pass |
| D2 | imports and uses `alembic` | FAIL | FAIL | FAIL | pass |

The description names two packages. **celery**: deepseek and gemini wire a `Celery` app; claude and gpt monitor a hand-rolled task model. **alembic**: only gemini runs Alembic migrations; the others (including deepseek) create tables directly, so they do not use the named migration tool.
