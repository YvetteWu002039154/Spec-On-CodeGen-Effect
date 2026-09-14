# Structural contract — `marginalia` **UML track**

Reference: origin repo `marginalia-main/src/marginalia/db/models/` — the ORM
model layer the class diagram was extracted from (modules `base`, `audit`,
`tasks`, `task_outcomes`, `ai_recall`, `ai_structural`, `user_visible`).

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of that model layer) and
grounded in the origin code. This particular extraction draws **no relationship
arrows** — it lists, for each class, its members (and, for `UtcDateTime`, its
methods). So the pinned facts are exactly the three things the diagram records:

1. **Classes** — the mixin/type classes (`Base`, `IdMixin`, `TimestampMixin`,
   `UtcDateTime`) plus the 15 ORM entities.
2. **Members under a class** — the `Mapped[...]` attributes drawn under each
   entity, and the two `TypeDecorator` methods under `UtcDateTime`.
3. **Member types** — the inner type of a `Mapped[T]` annotation (association-like).

Because the diagram lists `id` only under `IdMixin` and the timestamps only
under `TimestampMixin` (never repeated on the entities), the entities are
modelled as **inheriting** those shared superclasses; that convergence is pinned
too, grounded in the origin `class X(Base, IdMixin, ...)` declarations.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | entities converge on `Base` | every model is `class X(Base, ...)`; `Base(DeclarativeBase)` in `base.py:57` |
| U2 | entities converge on `IdMixin` | e.g. `class Task(Base, IdMixin)` `tasks.py:13`, `class File(Base, IdMixin, TimestampMixin)` `user_visible.py:88` (EntryTag is the sole exception — composite PK, `ai_structural.py:138`) |
| U3 | `UtcDateTime` methods `process_bind_param` / `process_result_value` | `base.py:33,40` (the only class with methods in the diagram) |
| U4 | `Base` members `metadata`, `type_annotation_map` | `base.py:58-59` |
| U5 | `TimestampMixin` members `created_at`, `updated_at` | `base.py:67,70` |
| U6 | `Task` queue field set | `tasks.py:44-62` (`kind/payload/status/priority/attempts/max_attempts/dedup_key/scheduled_at/lease_expires_at/locked_by/last_error/last_heartbeat_at/started_at/finished_at/created_at`) |
| U7 | `File` content-addressing field set | `user_visible.py:110-127` (`sha256/size_bytes/storage_key/mime_type/original_ext/kind/ingest_status/ingested_at/summary/description/extra/deleted_at`) |
| U8 | `Conversation` rolling-counter field set | `audit.py:132-150` (`session_id/turn_index/user_message/agent_response/tool_calls/llm_calls/total_*` counters/`started_at/ended_at`) |
| U9 | `Conversation.total_cost_estimate : Decimal` | `total_cost_estimate: Mapped[Decimal]` (`audit.py:148`, `Numeric(12,6)`) |
| U10 | `Catalog.is_system : bool` | `is_system: Mapped[bool]` (`ai_structural.py:65`, `Boolean`) |
