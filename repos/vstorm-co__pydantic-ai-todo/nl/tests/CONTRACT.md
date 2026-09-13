# Behavioral contract — `pydantic-ai-todo` **NL track**

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

## Dependency usage

> "Todo Toolset for Pydantic AI adds task planning capabilities to any Pydantic AI agent."

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `pydantic_ai` | FAIL | FAIL | FAIL | FAIL |
