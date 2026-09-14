# Behavioral contract — `planty` (m-danya__planty) **NL track**

## Description features

| Description feature |
| --- |
| A task carries a title |
| A task starts incomplete |
| Completing a task |
| Reopening a task |
| Grouping tasks in a container |
| Removing a task from a container |
| Priority (Todoist-inspired) |

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
