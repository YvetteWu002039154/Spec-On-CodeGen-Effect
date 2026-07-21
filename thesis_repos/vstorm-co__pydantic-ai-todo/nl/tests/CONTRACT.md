# Behavioral contract — `pydantic-ai-todo` **NL track**

Reference: origin package `pydantic-ai-todo-main/pydantic_ai_todo/` — chiefly
`toolset.py` (the task-management tools `create_todo_toolset` registers) plus the
`types.py` models and `storage.py` in-memory backend.

This contract is derived by comparing the **NL description**
(`nl/input/description.txt`) with the **origin code**, then pinning the observable
behaviors every reasonable implementation of that description would expose. The
description enumerates eight task-management features; each maps to an origin
tool. Behaviors are asserted on **observable effect** (a task shows up, a status
changes, a dependency gates the ready-list). Each generation is driven by its
own explicit driver (`adapter.py`) that names the exact classes and methods it
uses. A capability a generation does not expose — most importantly a generation
that only supports a real database and offers no in-memory path — is a
behavioral **FAILURE**: this suite does not skip / mark N/A. The driver attempts
the real API and the resulting error / empty result fails the test's assert.

## Description feature → origin grounding

| Description feature | Origin evidence (`pydantic_ai_todo/`) |
|---|---|
| Add a single task | `toolset.py::add_todo` (tool) → appends a `Todo`; `types.py::Todo` |
| List all tasks | `toolset.py::read_todos` renders `storage.get_todos()` |
| Update task status by ID | `toolset.py::update_todo_status` → `storage.update_todo(id, status=…)` |
| Delete task by ID | `toolset.py::remove_todo` → `storage.remove_todo(id)` |
| Create child task | `toolset.py::add_subtask` → `Todo(parent_id=…)` (subtasks enabled) |
| Link tasks with dependency | `toolset.py::set_dependency` → `Todo.depends_on` |
| List tasks ready to work on | `toolset.py::get_available_tasks` — excludes tasks with incomplete deps |
| Bulk write/update tasks | `toolset.py::write_todos(list[TodoItem])` replaces the list |
| Hierarchical view | `toolset.py::_format_hierarchical` nests children under parents |
| Status vocabulary | `types.py`: `pending | in_progress | completed | blocked` |

The four generations reinterpret the toolset as a `TodoToolset` **class** with
methods (`add_task`, `update_task_status`, `delete_task`, `create_child_task`,
`link_dependency`, `list_ready_tasks`, `bulk_write_tasks`, …). Each generation's
driver in `adapter.py` names the concrete classes/methods that generation
actually uses (e.g. claude's async in-memory `TodoToolset`, gpt's injected
`InMemoryTaskStorage`, deepseek's `TodoToolset(tenant_id, pool)`, gemini's
`TodoToolset(db_dsn)`).

## Behaviors pinned

### Create / read
- **N1. Add a task.** A single added task is then observable in the task list.
- **N2. List all tasks.** Listing returns all added tasks (count).

### Update / delete
- **N3. Update status by id.** Updating a task's status to `in_progress` is
  reflected in the task's status.
- **N4. Delete by id.** Deleting a task by id removes it from the list.

### Hierarchy / dependencies
- **N5. Create child task.** A child task references its parent (`parent_id`).
- **N6. Link dependency.** Two existing tasks can be linked with a dependency
  (recorded / acknowledged with a truthy result).
- **N7. Ready reflects dependencies.** A task blocked by an incomplete
  dependency is **excluded** from the ready list, and becomes ready once the
  dependency is completed.

### Bulk / hierarchical view
- **N8. Bulk write.** A bulk-write call creates multiple tasks at once.
- **N9. Hierarchical view.** The hierarchical listing nests a child under its
  parent (fewer roots than the flat listing).

## Notes on database-only generations

A generation that models storage **only** as PostgreSQL/`asyncpg` (deepseek) or
psycopg2 (gemini), with no in-memory backend, cannot be exercised headless: its
`TodoToolset` cannot be driven without a live database — deepseek's methods
dereference an absent connection pool, and gemini opens a psycopg2 connection in
its constructor. Because this suite does not skip, the driver attempts the real
API and every behavior **FAILS** (a genuine capability gap for a headless run).

## Dependency usage
The behaviors above are deliberately **dependency-agnostic** (the drivers
fake or stub external services), so a generation that reimplements a
dependency with a plain substitute still passes them. This section pins the
complementary axis — does a generation **import and use the package(s) the
description names**, rather than hand-roll a substitute?

> "Todo Toolset for Pydantic AI adds task planning capabilities to any Pydantic AI agent."

The check is **static** (`loader.dependency_used`, AST only — it never
imports the module, so it is independent of whether the package is installed).
A dependency passes when the file both **imports** the package *and*
**references** what it imported at least once (guarding against a dead
import). It is deliberately scoped to import-and-use, not correct-API
verification. A generation delivered as a full project directory passes if
any of its `.py` files imports-and-uses the package.

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `pydantic_ai` | FAIL | FAIL | FAIL | FAIL |

**None** of the four actually use `pydantic_ai`. claude imports `Agent`/`Tool` under a `try/except` but never references them (a **dead import**, which the AST check rejects); gpt, deepseek and gemini do not import it at all — they expose a plain toolset without the named agent framework.
