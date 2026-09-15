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

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `RetryActionHandler → ActionHandler` | `class RetryActionHandler(ActionHandler)` (`services/actions/retry_action.py:17`) |
| U2 | `SlackActionHandler → ActionHandler` | `class SlackActionHandler(ActionHandler)` (`services/actions/slack_action.py:15`) |
| U3 | `ActionHandler` methods | `execute` (abstract), `validate_params` (abstract), `render_template` (`services/actions/base.py`) |
| U4 | `RetryActionHandler` methods | overrides `execute` + `validate_params` (`retry_action.py:20,147`) |
| U5 | `SlackActionHandler` methods | overrides `execute` + `validate_params` (`slack_action.py:18,101`) |
| U6 | `ConnectionManager` methods | `connect/disconnect/set_client_filters/set_client_mode/send_personal_message/queue_*_broadcast/start_/stop_background_broadcaster` (`connection_manager.py`) |
| U7 | `CeleryEventMonitor` methods | `get_workers_info/set_task_callback/set_worker_callback/set_progress_callback/set_steps_callback/start_monitoring/stop` (`monitor.py:22,54–66,171,206`) |
| U8 | `EventHandler` methods | `handle_task_event/handle_worker_event/handle_progress_event/handle_steps_event` (`event_handler.py:21,27,57,70,83`) |
| U9 | `DatabaseManager` methods | `get_session` (`database.py:869`), `run_migrations` (`database.py:856`) |
| U10 | `EnvironmentDB.to_dict()` | `class EnvironmentDB(Base)` with `to_dict()` (`database.py:498`); the diagram draws `to_dict()` on the DB model boxes |
