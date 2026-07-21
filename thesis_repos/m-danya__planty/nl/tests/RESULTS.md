# Conformance results — `planty` (m-danya__planty) **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
Each is driven by its own explicit driver in `adapter.py`. `pass` = behavior
matches the contract · `FAIL` = capability wrong or **not exposed** (this suite
does not skip / mark N/A). Behaviors are derived by comparing
`nl/input/description.txt` with the origin `planty/domain/task.py` (see
[CONTRACT.md](CONTRACT.md)). Following the reference pattern, the behavioral
track has **no reference column**.

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  task carries its title | pass | pass | pass | pass |
| N2  new task is not completed | pass | pass | pass | pass |
| N3  completing marks it done | pass | pass | pass | pass |
| N4  a completed task can be reopened | pass | pass | pass | pass |
| N5  adding to a container lists it | pass | pass | pass | pass |
| N6  removing from a container empties it | pass | pass | pass | pass |
| N7  priority scale >= 4 levels | pass | pass | pass | pass |

**Totals:** 28 passed, 0 failed.

## Interpretation

Despite the one-line prompt, all four generations converge on the same
task-management essence, and every pinned behavior holds — the divergence is
purely *structural*, absorbed by driving each generation through its own
explicit driver, not behavioral:

- **Task lifecycle shape.** claude/deepseek/gemini put `complete()` /
  `reopen()`-or-`uncomplete()` on the `Task` object; gpt makes `Task` an
  **immutable** frozen dataclass with a `status` enum and drives completion
  through a `Planty` manager (`complete_task`/`reopen_task`), so its driver
  re-fetches the task by id after each mutation. Both express the same
  observable N3/N4 behavior.
- **Completion state.** claude exposes `is_completed()` as a **method** (its
  driver calls it); deepseek exposes an `is_completed` **property** and gemini a
  plain `is_completed` **attribute** (read directly); gpt reads
  `status == Status.DONE` on the re-fetched frozen task.
- **Container shape.** claude/deepseek/gemini expose object containers
  (`Project` with `add_task`/`remove_task`), counted via `.tasks`,
  `get_all_tasks()`, or `get_tasks(include_completed=True)` respectively; gpt has
  no mutable container object and instead groups tasks by `project_id` inside the
  manager (`create_project` + `list_tasks` + `delete_task`). Removal keys on the
  task **id** for claude and the task **object** for deepseek/gemini — each
  driver uses the shape its generation implements.
- **Title / priority.** claude/deepseek/gemini carry the title on `Task.title`;
  gpt on `Task.content`. All four ship a 4-level priority enum, though the
  vocabulary differs (`P1..P4` in gpt/deepseek/gemini, `LOW/MEDIUM/HIGH/URGENT`
  in claude), so N7 is pinned on the level count, not the names.

## Classification

- **No FAIL.** These seven behaviors are the core of a Todoist/GTD task manager,
  and each generation is a complete such manager, so all-pass is the honest
  outcome. The observed state transitions (`new=open → complete=done →
  reopen=open`, and `add → count 1 → remove → count 0`) confirm the checks are
  exercised rather than vacuous.

## Reproduce

```bash
cd thesis_repos/m-danya__planty/nl/tests
python3 -m pytest -p no:warnings -q
```
