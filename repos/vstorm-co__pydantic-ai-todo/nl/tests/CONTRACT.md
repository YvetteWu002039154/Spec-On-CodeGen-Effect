# Behavioral contract — `pydantic-ai-todo` **NL track**

## Description features

| Description feature |
|---|
| Add a single task |
| List all tasks |
| Update task status by ID |
| Delete task by ID |
| Create child task |
| Link tasks with dependency |
| List tasks ready to work on |
| Bulk write/update tasks |
| Hierarchical view |
| Status vocabulary |

The four generations reinterpret the toolset as a `TodoToolset` **class** with
methods (`add_task`, `update_task_status`, `delete_task`, `create_child_task`,
`link_dependency`, `list_ready_tasks`, `bulk_write_tasks`, …). Each generation's
driver in `adapter.py` names the concrete classes/methods that generation
actually uses (e.g. claude's async in-memory `TodoToolset`, gpt's injected
`InMemoryTaskStorage`, deepseek's `TodoToolset(tenant_id, pool)`, gemini's
`TodoToolset(db_dsn)`).

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Create / read | **Add a task.** A single added task is then observable in the task list. |
| N2 | Create / read | **List all tasks.** Listing returns all added tasks (count). |
| N3 | Update / delete | **Update status by id.** Updating a task's status to `in_progress` is reflected in the task's status. |
| N4 | Update / delete | **Delete by id.** Deleting a task by id removes it from the list. |
| N5 | Hierarchy / dependencies | **Create child task.** A child task references its parent (`parent_id`). |
| N6 | Hierarchy / dependencies | **Link dependency.** Two existing tasks can be linked with a dependency (recorded / acknowledged with a truthy result). |
| N7 | Hierarchy / dependencies | **Ready reflects dependencies.** A task blocked by an incomplete dependency is **excluded** from the ready list, and becomes ready once the dependency is completed. |
| N8 | Bulk / hierarchical view | **Bulk write.** A bulk-write call creates multiple tasks at once. |
| N9 | Bulk / hierarchical view | **Hierarchical view.** The hierarchical listing nests a child under its parent (fewer roots than the flat listing). |

## Dependency usage

> "Todo Toolset for Pydantic AI adds task planning capabilities to any Pydantic AI agent."

| # | Check |
|---|---|
| D1 | imports and uses `pydantic_ai` |
