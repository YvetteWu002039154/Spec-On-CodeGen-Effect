# Structural contract — `planty` (m-danya__planty) **UML track**

Reference for grounding: origin module `planty-main/planty/domain/task.py` — the
pure-domain layer the class diagram draws its entity hierarchy, associations, and
method sets from (grounding only; not a test subject).

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction of the `planty` package) and
grounded in that origin code. A class diagram records *structure*, not runtime
behavior, so the pinned facts are the three things the diagram actually draws:

1. **Inheritance links** — `Child --|> Parent`.
2. **Association links** — `A --> B : attr` (an attribute of `A` is typed as `B`).
3. **Methods under a class** — the `Task` / `Section` domain operations.

Scope: the diagram spans the domain layer (`domain/task.py`), the ORM models
(`infrastructure/models.py`), the repositories, and the unit-of-work
(`application/uow.py`). The pinned facts are taken from the **pure-domain
layer** (`domain/task.py`), the part every generation reproduces; the
ORM/repository/UoW classes are framework plumbing whose real
`--|> Base` links vanish under the (necessary) sqlalchemy stub, so they are out
of scope.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `Task/Section/User/RecurrenceInfo/Attachment --|> Entity` | all five are `class X(Entity)`; `Entity(BaseModel)` (L28, L34, L40, L46, L117, L250) |
| U2 | `Task --|> Entity` | `class Task(Entity)` (L46) |
| U3 | `Section --|> Entity` | `class Section(Entity)` (L117) |
| U4 | `Section --> Task : tasks` | `tasks: list[Task]` (L124) |
| U5 | `Section --> Section : subsections` | `subsections: list["Section"]` (L125) |
| U6 | `Task --> Attachment : attachments` | `attachments: list["Attachment"]` (L62) |
| U7 | `Task --> RecurrenceInfo : recurrence` | `recurrence: Optional[RecurrenceInfo]` (L60) |
| U8 | `Task` lifecycle methods | `mark_completed` (L79), `toggle_completed` (L92), `archive` (L110), `unarchive` (L113) |
| U9 | `Task` attachment methods | `add_attachment` (L104), `remove_attachment` (L107) |
| U10 | `Section` membership methods | `insert_task` (L186), `remove_task` (L195), `insert_subsection` (L214), `remove_subsection` (L225) |
