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

## Diagram fact → origin grounding

| Diagram fact | Origin evidence (`planty/domain/task.py`) |
|---|---|
| `Task/Section/User/RecurrenceInfo/Attachment --|> Entity` | all five are `class X(Entity)`; `Entity(BaseModel)` (L28, L34, L40, L46, L117, L250) |
| `Task --|> Entity` | `class Task(Entity)` (L46) |
| `Section --|> Entity` | `class Section(Entity)` (L117) |
| `Section --> Task : tasks` | `tasks: list[Task]` (L124) |
| `Section --> Section : subsections` | `subsections: list["Section"]` (L125) |
| `Task --> Attachment : attachments` | `attachments: list["Attachment"]` (L62) |
| `Task --> RecurrenceInfo : recurrence` | `recurrence: Optional[RecurrenceInfo]` (L60) |
| `Task` lifecycle methods | `mark_completed` (L79), `toggle_completed` (L92), `archive` (L110), `unarchive` (L113) |
| `Task` attachment methods | `add_attachment` (L104), `remove_attachment` (L107) |
| `Section` membership methods | `insert_task` (L186), `remove_task` (L195), `insert_subsection` (L214), `remove_subsection` (L225) |

## Facts pinned

### Inheritance links (`--|>`)
- **U1. Shared entity base.** The five pure-domain entities `Task`, `Section`,
  `User`, `RecurrenceInfo`, `Attachment` converge on a **common base class**
  (`Entity`). Asserted on convergence, not the base's literal name.
- **U2. `Task --|> Entity`.** `Task` is a proper subclass of `Entity`.
- **U3. `Section --|> Entity`.** `Section` is a proper subclass of `Entity`.

### Association links (`--> : attr`)
- **U4. `Section --> Task`.** `Section.tasks`'s annotation references `Task`.
- **U5. `Section --> Section`.** `Section.subsections`'s annotation references
  `Section` (the self-referential subsection tree).
- **U6. `Task --> Attachment`.** `Task.attachments`'s annotation references
  `Attachment`.
- **U7. `Task --> RecurrenceInfo`.** `Task.recurrence`'s annotation references
  `RecurrenceInfo` (not `Any` / an inline literal).

### Methods under a class
- **U8. Task lifecycle.** `Task` defines `mark_completed`, `toggle_completed`,
  `archive`, and `unarchive`.
- **U9. Task attachments.** `Task` defines `add_attachment` and `remove_attachment`.
- **U10. Section membership.** `Section` defines `insert_task`, `remove_task`,
  `insert_subsection`, and `remove_subsection`.

## Harness

The pinned surface is the **structure the class diagram draws** — inheritance
links (`--|>`), association links (`--> : attr`), and the `Task` / `Section`
domain method sets — asserted by **reflection on the loaded classes** (subclass
relations, attribute annotations, method names), never by executing behavior. A pinned method must be a **real (non-stub) implementation**: a body that is only `pass` / `...` / `return None` / `raise NotImplementedError` is judged statically (from source, never executed) as *not* implemented and fails the method set. A
class or attribute a generation does not define is a **FAILURE**, as is a
structural mismatch (the class exists but the link/method is wrong or
absent). This track does not skip / mark N/A. Subjects are the 4 UML generations
(`uml/outputcode/{claude,gpt,deepseek,gemini}`); the origin `domain/task.py` the
diagram was extracted from grounds the facts above but is not itself a test
subject.

## Portability

- The contract is structural, so the loader installs a permissive import finder
  that stubs the heavy stack (sqlalchemy, fastapi, dateutil, …) while keeping
  **pydantic real** — the domain entities then build as genuine classes with
  their annotations intact. sqlalchemy is stubbed on purpose so the four
  generations' `*Model` ORM classes never collide over a shared `MetaData`.
- The adapter resolves classes by bare name, first-definition-wins, so the
  domain `Task`/`Section` (declared before `TaskModel`/`SectionModel`) are the
  ones reflected on.
