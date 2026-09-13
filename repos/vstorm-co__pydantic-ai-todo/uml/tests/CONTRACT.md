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

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| `TodoEventType --* TodoEvent : event_type` | `events.py::TodoEvent.event_type: TodoEventType` (L63) |
| `Todo --* TodoEvent : todo` | `events.py::TodoEvent.todo: Todo` (L64) |
| `Todo { id, content, status, active_form, parent_id, depends_on }` | `types.py::Todo` (L24–29) |
| `TodoItem { … same six … }` | `types.py::TodoItem` (L39–65) |
| `TodoStatusUpdate { todo_id, status }` | `types.py::TodoStatusUpdate` (L74–78) |
| `AsyncMemoryStorage { add/get/get_all/remove/set/update _todo }` | `storage.py::AsyncMemoryStorage` (L181–281) |
| `AsyncPostgresStorage { …CRUD…, initialize, close }` | `storage.py::AsyncPostgresStorage` (`initialize` L362, `close` L375) |
| `AsyncRedisStorage { …CRUD…, initialize, close }` | `storage.py::AsyncRedisStorage` (`initialize` L687, `close` L703) |
| `TodoEventEmitter { emit, off, on, on_created/completed/updated/deleted/status_changed }` | `events.py::TodoEventEmitter` (L101–205) |
| `TodoCapability { get_instructions, get_serialization_name, get_toolset }` | `capability.py::TodoCapability` (L93–118) |

## Facts pinned

### Composition links (`--* : attr`)
- **U1. `TodoEventType --* TodoEvent`.** `TodoEvent.event_type`'s annotation
  references `TodoEventType`.
- **U2. `Todo --* TodoEvent`.** `TodoEvent.todo`'s annotation references `Todo`.

### Attributes under a class
- **U3. `Todo` fields.** Carries `id`, `content`, `status`, `active_form`,
  `parent_id`, `depends_on`.
- **U4. `TodoItem` fields.** Carries the same six fields.
- **U5. `TodoStatusUpdate` fields.** Carries `todo_id` and `status`.

### Methods under a class
- **U6. `AsyncMemoryStorage` CRUD.** Defines `add_todo`, `get_todo`, `get_todos`,
  `remove_todo`, `set_todos`, `update_todo`.
- **U7. `AsyncPostgresStorage`.** Defines the CRUD set plus `initialize`/`close`.
- **U8. `AsyncRedisStorage`.** Defines the CRUD set plus `initialize`/`close`.
- **U9. `TodoEventEmitter` method set.** Defines `emit`, `off`, `on`,
  `on_created`, `on_completed`, `on_updated`, `on_deleted`, `on_status_changed`.
- **U10. `TodoCapability` method set.** Defines `get_instructions`,
  `get_serialization_name`, `get_toolset`.

## Harness

The pinned surface is the **structure the class diagram draws** — composition
links (`--* : attr`), the fields it lists on the model classes, and the methods it
lists on the storage / emitter / capability classes — asserted by **reflection on
the loaded classes** (attribute annotations, `__annotations__` / pydantic
`model_fields`, method names), never by executing behavior. A pinned method must be a **real (non-stub) implementation**: a body that is only `pass` / `...` / `return None` / `raise NotImplementedError` is judged statically (from source, never executed) as *not* implemented and fails the method set. A class or attribute a
generation does not define is a **FAILURE**, as is a structural mismatch (the
class exists but the link/field/method is wrong or absent). This track does not
skip / mark N/A.
Subjects are the 4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`);
the origin package the diagram was extracted from grounds the facts above but is
not itself a test subject.

## Portability

Some impls import a heavy stack (`pydantic_ai`, `asyncpg`, `redis`, `psycopg2`, …)
at module top, but the contract is purely structural. The loader installs a
permissive import finder that resolves those to stubs, so every module execs far
enough to *define* its classes on a machine with only `pydantic` + the standard
library. The stub declines to fabricate dunder attributes, so a generation's
`@dataclass TodoCapability(AbstractCapability[Any])` (whose stubbed base would
otherwise present an infinitely-iterable fake `__dataclass_fields__`) loads
cleanly.

## Note on attributes vs. methods

The diagram also lists attributes on `TodoCapability` (`storage`,
`async_storage`, `enable_subtasks`, `descriptions`). Those are assigned as
*instance* attributes inside `__init__` in every generation, so they carry no
class-level annotations and are not reflectable without instantiation (which the
structural track forbids). U10 therefore pins the reliably-reflectable
`TodoCapability` **methods**. `Todo`/`TodoItem`/`TodoStatusUpdate` fields (U3–U5)
*are* reflectable because those are dataclasses / pydantic models with
class-level annotations in every generation.
