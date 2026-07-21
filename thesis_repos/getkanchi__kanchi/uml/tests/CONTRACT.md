# Structural contract — `Kanchi` **UML track**

Reference: 
- origin repo `kanchi-main/agent/`
- `uml/input/classes.puml`

1. **Inheritance links** — `Child --|> Parent` (the diagram lists exactly two:
   the two action handlers specializing `ActionHandler`).
2. **Methods under a class** — the operations pyreverse lists inside each class
   box.

> The diagram draws **no `-->` association links** for this repo (attributes are
> listed as untyped fields, not typed associations), so there is no association
> fact to pin — unlike the NexusCtrl UML reference, which had `--> : attr`
> edges. This is a property of the extracted diagram, recorded here for
> traceability.

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| `RetryActionHandler → ActionHandler` | `class RetryActionHandler(ActionHandler)` (`services/actions/retry_action.py:17`) |
| `SlackActionHandler → ActionHandler` | `class SlackActionHandler(ActionHandler)` (`services/actions/slack_action.py:15`) |
| `ActionHandler` methods | `execute` (abstract), `validate_params` (abstract), `render_template` (`services/actions/base.py`) |
| `RetryActionHandler` methods | overrides `execute` + `validate_params` (`retry_action.py:20,147`) |
| `SlackActionHandler` methods | overrides `execute` + `validate_params` (`slack_action.py:18,101`) |
| `ConnectionManager` methods | `connect/disconnect/set_client_filters/set_client_mode/send_personal_message/queue_*_broadcast/start_/stop_background_broadcaster` (`connection_manager.py`) |
| `CeleryEventMonitor` methods | `get_workers_info/set_task_callback/set_worker_callback/set_progress_callback/set_steps_callback/start_monitoring/stop` (`monitor.py:22,54–66,171,206`) |
| `EventHandler` methods | `handle_task_event/handle_worker_event/handle_progress_event/handle_steps_event` (`event_handler.py:21,27,57,70,83`) |
| `DatabaseManager` methods | `get_session` (`database.py:869`), `run_migrations` (`database.py:856`) |
| `EnvironmentDB.to_dict()` | `class EnvironmentDB(Base)` with `to_dict()` (`database.py:498`); the diagram draws `to_dict()` on the DB model boxes |

## Facts pinned

### Inheritance links (`--|>`)
- **U1. `RetryActionHandler --|> ActionHandler`.** Proper subclass.
- **U2. `SlackActionHandler --|> ActionHandler`.** Proper subclass.

### Methods under a class
- **U3. `ActionHandler` method set.** Defines `execute`, `validate_params`,
  `render_template`.
- **U4. `RetryActionHandler` overrides.** *Directly defines* `execute`,
  `validate_params` as concrete (non-abstract, non-stub) methods — an inherited
  or still-abstract one does not satisfy the override.
- **U5. `SlackActionHandler` overrides.** *Directly defines* `execute`,
  `validate_params` as concrete (non-abstract, non-stub) methods.
- **U6. `ConnectionManager` method set.** Defines `connect`, `disconnect`,
  `set_client_filters`, `set_client_mode`, `send_personal_message`, the four
  `queue_*_broadcast` fan-out entry points, and `start_/stop_background_broadcaster`.
- **U7. `CeleryEventMonitor` method set.** Defines `get_workers_info`, the four
  callback setters (`set_task_callback`, `set_worker_callback`,
  `set_progress_callback`, `set_steps_callback`), `start_monitoring`, `stop`.
- **U8. `EventHandler` method set.** Defines the four event dispatch operations
  `handle_task_event`, `handle_worker_event`, `handle_progress_event`,
  `handle_steps_event`.
- **U9. `DatabaseManager` method set.** Defines `get_session` and
  `run_migrations`.
- **U10. `EnvironmentDB.to_dict()`.** Exposes `to_dict()` (representative of the
  serialization operation the diagram draws across the `*DB` model boxes).

## Harness

The pinned surface is the **structure the class diagram draws** — the two
inheritance links (`--|>`) and the method sets pyreverse lists under each class —
asserted by **static reflection on the loaded classes** (subclass relations,
method definitions), never by executing behavior. A required method must be a
**real definition**: a name present only as an empty / `pass` / `...` /
`raise NotImplementedError` body does *not* satisfy the fact (checked by static
AST analysis of the method source, no execution). An `@abstractmethod` on the
abstract base is accepted; a specialization's override (U4/U5) must be directly
defined and concrete. A class or method a generation does not define is a **FAILURE** —
as is a present class with a wrong inheritance link, or a required method that
is missing or present only as a stub. This track does not skip / mark N/A. Subjects are the 4 UML
generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`); the origin `agent`
package is not a test subject, only the grounding for the facts above.

## Portability

The generations import a heavy third-party stack (fastapi, sqlalchemy, celery,
pydantic, redis, prometheus_client, …) at module top; the loader keeps every
dependency **real** (no stubbing) and each module execs far enough to define its
classes cleanly. Inheritance from a real `Base = declarative_base()` is therefore
genuine, not stub-preserved.
