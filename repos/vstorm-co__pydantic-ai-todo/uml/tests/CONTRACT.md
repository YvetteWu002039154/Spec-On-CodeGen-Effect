# Structural contract — `pydantic-ai-todo` **UML track**

Reference: origin package `pydantic-ai-todo-main/pydantic_ai_todo/` — the modules
(`types.py`, `events.py`, `storage.py`, `capability.py`) the class diagram was
extracted from.

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the origin package) and
grounded in that origin code. A class diagram records *structure*, not runtime
behavior, so the pinned facts are the three things this diagram actually draws:

1. **Composition links** — `A --* B : attr` (an attribute of `B` is typed as `A`).
2. **Attributes under a class** — the fields the diagram lists on a class.
3. **Methods under a class** — the operations the diagram lists on a class.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `TodoEventType --* TodoEvent : event_type` | `events.py::TodoEvent.event_type: TodoEventType` (L63) |
| U2 | `Todo --* TodoEvent : todo` | `events.py::TodoEvent.todo: Todo` (L64) |
| U3 | `Todo { id, content, status, active_form, parent_id, depends_on }` | `types.py::Todo` (L24–29) |
| U4 | `TodoItem { … same six … }` | `types.py::TodoItem` (L39–65) |
| U5 | `TodoStatusUpdate { todo_id, status }` | `types.py::TodoStatusUpdate` (L74–78) |
| U6 | `AsyncMemoryStorage { add/get/get_all/remove/set/update _todo }` | `storage.py::AsyncMemoryStorage` (L181–281) |
| U7 | `AsyncPostgresStorage { …CRUD…, initialize, close }` | `storage.py::AsyncPostgresStorage` (`initialize` L362, `close` L375) |
| U8 | `AsyncRedisStorage { …CRUD…, initialize, close }` | `storage.py::AsyncRedisStorage` (`initialize` L687, `close` L703) |
| U9 | `TodoEventEmitter { emit, off, on, on_created/completed/updated/deleted/status_changed }` | `events.py::TodoEventEmitter` (L101–205) |
| U10 | `TodoCapability { get_instructions, get_serialization_name, get_toolset }` | `capability.py::TodoCapability` (L93–118) |

## Note on attributes vs. methods

The diagram also lists attributes on `TodoCapability` (`storage`,
`async_storage`, `enable_subtasks`, `descriptions`). Those are assigned as
*instance* attributes inside `__init__` in every generation, so they carry no
class-level annotations and are not reflectable without instantiation (which the
structural track forbids). U10 therefore pins the reliably-reflectable
`TodoCapability` **methods**. `Todo`/`TodoItem`/`TodoStatusUpdate` fields (U3–U5)
*are* reflectable because those are dataclasses / pydantic models with
class-level annotations in every generation.
