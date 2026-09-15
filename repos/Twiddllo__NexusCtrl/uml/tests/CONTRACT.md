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

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | User/Project/Server/Task/MetricSnapshot/AuditLog ➝ Base | all six are `class X(Base)` ORM models; `Base` is the declarative base (L47) |
| U2 | TaskCreate ➝ TaskBase | `class TaskCreate(TaskBase)` (L353) |
| U3 | TaskResponse ➝ TaskBase | `class TaskResponse(TaskBase)` (L367) |
| U4 | TaskBase → TaskPriority : priority | `priority: TaskPriority = TaskPriority.MEDIUM` (L347) |
| U5 | TaskBase → TaskStatus : status | `status: TaskStatus = TaskStatus.TODO` (L346) |
| U6 | TokenResponse → UserResponse : user | `user: UserResponse` (L249) |
| U7 | MetricsConnectionManager methods — Manager method set | `connect_client/disconnect_client/connect_agent/disconnect_agent/broadcast_to_clients` (L416–444) |
| U8 | MetricsConnectionManager methods — Client lifecycle | `connect_client/disconnect_client/connect_agent/disconnect_agent/broadcast_to_clients` (L416–444) |
| U9 | MetricsConnectionManager methods — Agent lifecycle | `connect_client/disconnect_client/connect_agent/disconnect_agent/broadcast_to_clients` (L416–444) |
| U10 | MetricsConnectionManager methods — Fan-out | `connect_client/disconnect_client/connect_agent/disconnect_agent/broadcast_to_clients` (L416–444) |
