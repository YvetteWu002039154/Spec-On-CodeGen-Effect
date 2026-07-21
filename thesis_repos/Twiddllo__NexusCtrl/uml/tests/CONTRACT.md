# Structural contract — `NexusCtrl` **UML track**

Reference: origin repo `NexusCtrl-main/backend/app.py`

This contract is derived from the **UML class diagram** and grounded in that origin code. The pinned facts are the three things the diagram actually draws:

1. **Inheritance links** — `Child ➝ Parent` (UML: `--|>`)
2. **Association links** — `A → B : attr` (UML: `-->`) (an attribute of `A` is typed as `B`).
3. **Methods under a class** — only `MetricsConnectionManager` carries any.

Facts are asserted by **reflection on the loaded classes** (subclass relations,
attribute annotations, method names) — never by executing behavior. Any fact the
diagram specifies but a generation does not implement — a missing class, a
missing or wrong inheritance/association link, a missing or stubbed method — is a
**FAILURE**. This track has **no skip / N/A**.

## Diagram fact → origin grounding

| Diagram fact | Origin evidence (`app.py`) |
|---|---|
| User/Project/Server/Task/MetricSnapshot/AuditLog ➝ Base | all six are `class X(Base)` ORM models; `Base` is the declarative base (L47) |
| TaskCreate ➝ TaskBase | `class TaskCreate(TaskBase)` (L353) |
| TaskResponse ➝ TaskBase | `class TaskResponse(TaskBase)` (L367) |
| TaskBase → TaskPriority : priority | `priority: TaskPriority = TaskPriority.MEDIUM` (L347) |
| TaskBase → TaskStatus : status | `status: TaskStatus = TaskStatus.TODO` (L346) |
| TokenResponse → UserResponse : user | `user: UserResponse` (L249) |
| MetricsConnectionManager methods | `connect_client/disconnect_client/connect_agent/disconnect_agent/broadcast_to_clients` (L416–444) |

## Behaviors pinned

### Inheritance links (➝)
- **U1. Shared entity base.** The six ORM entities `User`, `Project`, `Server`,
  `Task`, `MetricSnapshot`, `AuditLog` converge on a **common base class**.
  Asserted on convergence, not the base's literal name, since `class Base(...)`
  and `Base = declarative_base()` name the base differently.
- **U2. TaskCreate ➝ TaskBase.** `TaskCreate` is a proper subclass of `TaskBase`.
- **U3. TaskResponse ➝ TaskBase.** `TaskResponse` is a proper subclass of `TaskBase`.

### Association links (→ : attr)
- **U4. TaskBase → TaskPriority.** `TaskBase.priority`'s type annotation
  references `TaskPriority` (not `Any`/`str`/an inline literal).
- **U5. TaskBase → TaskStatus.** `TaskBase.status`'s annotation references
  `TaskStatus`.
- **U6. TokenResponse → UserResponse.** `TokenResponse.user`'s annotation
  references `UserResponse`.

### Methods under a class
- **U7. Manager method set.** `MetricsConnectionManager` defines the full
  connection-management set with real implementations (not stubs):
  `connect_client`, `disconnect_client`, `connect_agent`, `disconnect_agent`,
  `broadcast_to_clients`.
- **U8. Client lifecycle.** It exposes both `connect_client` and `disconnect_client`
  with working bodies.
- **U9. Agent lifecycle.** It exposes both `connect_agent` and `disconnect_agent`
  with working bodies.
- **U10. Fan-out.** It exposes `broadcast_to_clients` (the distinctive method that
  pushes one payload to every subscribed client) with a working body.

## Harness

The pinned surface is the **structure the class diagram draws** — inheritance
links (`--|>`), association links (`--> : attr`), and the methods under
`MetricsConnectionManager` — asserted by **reflection on the loaded classes**
(subclass relations, attribute annotations, method names), never by executing
behavior. Any fact the diagram specifies but a generation does not implement — a
missing class, a missing or wrong inheritance/association link, a missing or
stubbed method — is a **FAILURE**; this track has **no skip / N/A**. Subjects are
the 4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`); the origin
`app.py` the diagram was extracted from grounds the facts above but is not itself
a test subject.

## Portability

Several impls import a heavy third-party stack (fastapi, pydantic, sqlalchemy, …)
at module top, so those packages must be importable in the environment for each
module to exec far enough to define its classes.