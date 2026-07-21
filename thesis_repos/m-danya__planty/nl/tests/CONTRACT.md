# Behavioral contract — `planty` (m-danya__planty) **NL track**

Reference for grounding: origin `planty-main/planty/domain/task.py` (the pure
`Task` / `Section` domain layer).

This contract is derived by comparing the **NL description**
(`nl/input/description.txt`) with the **origin code**, then pinning the
observable behaviors every reasonable implementation of that description would
expose. The description is a single line —

> "Planty is an open-source task management app inspired by Todoist and the GTD
> system."

so the four generations reinterpret it as **structurally divergent Todoist/GTD
models** (rich OO with `Task`/`Project`/`Section` in claude/deepseek/gemini; an
immutable `Task` + a `Planty` manager keyed by `project_id` in gpt). The pinned
behaviors are therefore the *task-management essence* common to the description
and the origin, asserted on **observable capability and effect**. Each
generation is driven by its own explicit driver (`adapter.py`) that names the
exact classes and methods it uses. A capability a generation does not expose is
a behavioral **FAILURE** — this suite does not skip / mark N/A.

Following the reference pattern, the NL/behavioral track carries **no reference
column**: the origin's domain model (server-scoped `Section`/`RecurrenceInfo`
with a due-date roll-forward) is far richer than the one-line description
elicits, so it is not a fair behavioral peer to the Todoist-style generations.

## Description feature → origin grounding

| Description feature | Origin evidence (`planty/domain/task.py`) |
|---|---|
| A task carries a title | `Task.title: str` (required field, L50) |
| A task starts incomplete | `Task.is_completed: bool = False` (L53) |
| Completing a task | `Task.mark_completed()` → `is_completed = True` (L79, L88) |
| Reopening a task | `Task.toggle_completed()` flips a completed task back (L92-97) |
| Grouping tasks in a container | `Section.insert_task(task)` appends to `Section.tasks` (L186-193) |
| Removing a task from a container | `Section.remove_task(task)` drops it from `Section.tasks` (L195-200) |
| Priority (Todoist-inspired) | *not in origin*; grounded in the description's "inspired by Todoist" — Todoist's hallmark is a 4-level priority (P1-P4). All four generations model a 4-member priority enum. |

## Behaviors pinned

### Task creation
- **N1. Title carried.** A task created with a title/content carries that value
  back on the created object.
- **N2. Starts incomplete.** A freshly created task is **not** in a completed
  state.

### Completion lifecycle
- **N3. Completion observable.** Completing a task moves it to a completed/done
  state that is observable.
- **N4. Reopenable.** A completed task can be reopened / uncompleted back to a
  not-done state.

### Container grouping
- **N5. Add lists it.** Adding a task to a container (project/section, or a
  manager-keyed project bucket) makes the container report exactly that one task.
- **N6. Remove empties it.** Removing the task from its container leaves the
  container with no tasks.

### Priority (Todoist-inspired)
- **N7. Priority scale.** Tasks support a priority scale with **at least four**
  levels (Todoist P1-P4 / equivalent). Grounded in the description rather than
  the origin (which does not model priority); pinned on the level *count*, not
  the specific names, since the generations disagree on the vocabulary
  (`P1..P4` vs `LOW/MEDIUM/HIGH/URGENT`).

## Notes for the drivers

Each generation has one explicit driver (`adapter.py`) with one method per
behavior (N1..N7), in order, naming the concrete API it uses:

- **Task lifecycle.** claude/deepseek/gemini put lifecycle on the `Task` object
  (`complete()` + `reopen()`-or-`uncomplete()`); the driver reads completion via
  claude's `is_completed()` **method**, or deepseek/gemini's `is_completed`
  attribute/property. gpt makes `Task` an **immutable** frozen dataclass with a
  `status` enum and drives lifecycle through a `Planty` manager
  (`create_task`/`complete_task`/`reopen_task`), re-fetching the task by id after
  each mutation and reading `status == Status.DONE`.
- **Containers.** claude/deepseek/gemini expose object containers (`Project`
  with `add_task` + `remove_task`), read via `.tasks` (claude),
  `get_all_tasks()` (deepseek), or `get_tasks(include_completed=True)` (gemini);
  claude removes **by task id**, deepseek/gemini **by task object**. gpt has no
  mutable container object and instead groups tasks by `project_id` inside the
  manager (`create_project` + `list_tasks(project_id=...)` + `delete_task`).
- **Title / priority.** claude/deepseek/gemini use `Task.title`; gpt uses
  `Task.content`. All four ship a 4-level `Priority` enum (`P1..P4`, or
  `LOW/MEDIUM/HIGH/URGENT` in claude), so N7 is pinned on the level count.
