# Behavioral contract — `planty` (m-danya__planty) **NL track**

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
