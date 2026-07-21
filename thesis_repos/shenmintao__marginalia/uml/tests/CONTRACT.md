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

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| entities converge on `Base` | every model is `class X(Base, ...)`; `Base(DeclarativeBase)` in `base.py:57` |
| entities converge on `IdMixin` | e.g. `class Task(Base, IdMixin)` `tasks.py:13`, `class File(Base, IdMixin, TimestampMixin)` `user_visible.py:88` (EntryTag is the sole exception — composite PK, `ai_structural.py:138`) |
| `UtcDateTime` methods `process_bind_param` / `process_result_value` | `base.py:33,40` (the only class with methods in the diagram) |
| `Base` members `metadata`, `type_annotation_map` | `base.py:58-59` |
| `TimestampMixin` members `created_at`, `updated_at` | `base.py:67,70` |
| `Task` queue field set | `tasks.py:44-62` (`kind/payload/status/priority/attempts/max_attempts/dedup_key/scheduled_at/lease_expires_at/locked_by/last_error/last_heartbeat_at/started_at/finished_at/created_at`) |
| `File` content-addressing field set | `user_visible.py:110-127` (`sha256/size_bytes/storage_key/mime_type/original_ext/kind/ingest_status/ingested_at/summary/description/extra/deleted_at`) |
| `Conversation` rolling-counter field set | `audit.py:132-150` (`session_id/turn_index/user_message/agent_response/tool_calls/llm_calls/total_*` counters/`started_at/ended_at`) |
| `Conversation.total_cost_estimate : Decimal` | `total_cost_estimate: Mapped[Decimal]` (`audit.py:148`, `Numeric(12,6)`) |
| `Catalog.is_system : bool` | `is_system: Mapped[bool]` (`ai_structural.py:65`, `Boolean`) |

## Facts pinned

### Inheritance convergence (mixins drawn as standalone superclasses)
- **U1. Shared declarative base.** `Task/File/Folder/Catalog/Conversation/Session`
  converge on a common `Base` class.
- **U2. Shared identity mixin.** The same id-bearing entities converge on
  `IdMixin`. (`EntryTag` is excluded — it has a composite PK and no `IdMixin` in
  the origin.)

### Methods under a class
- **U3. UtcDateTime hook pair.** `UtcDateTime` defines both `process_bind_param`
  and `process_result_value` (the `TypeDecorator` hooks — the only methods the
  diagram draws).

### Members under a class
- **U4. Base infrastructure.** `Base` carries `metadata` and `type_annotation_map`.
- **U5. TimestampMixin.** carries `created_at` and `updated_at`.
- **U6. Task queue fields.** `Task` carries its full async-queue field set.
- **U7. File content fields.** `File` carries its content-addressing field set.
- **U8. Conversation counters.** `Conversation` carries its rolling-counter set.

### Member types (`Mapped[T]` inner type)
- **U9. `Conversation.total_cost_estimate --> Decimal`.** the money field is
  typed `Decimal` (not `float`/`str`/`Any`).
- **U10. `Catalog.is_system --> bool`.** the system flag is typed `bool`.

## Harness

The pinned surface is the **structure the class diagram draws** — classes, the
members under each class, the two `TypeDecorator` hooks under `UtcDateTime`, and
the `Mapped[T]` inner types — asserted by **reflection on the loaded classes**
(`issubclass`, `__mro__`, `__annotations__`, method names), never by executing
behavior. A pinned method must be a **real (non-stub) implementation**: a body that is only `pass` / `...` / `return None` / `raise NotImplementedError` is judged statically (from source, never executed) as *not* implemented and fails the method set. A class or member a generation does not define is a **FAILURE**,
as is a structural mismatch (present but wrong type / missing method). This track
does not skip / mark N/A.
Subjects are the 4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`);
the origin ORM model layer the diagram was extracted from grounds the facts above
but is not itself a test subject.

## Portability

SQLAlchemy is a hard dependency of the origin and every generation and is
installed here, so it is kept **real** — that preserves the `Mapped[...]`
annotations the attribute-type facts (U9/U10) read. Only a genuinely-missing
optional top would be stubbed; none were.
