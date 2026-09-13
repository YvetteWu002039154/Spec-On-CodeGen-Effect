# Conformance results — `planty` (m-danya__planty) **UML track**

Reference: origin `planty-main/planty/domain/task.py` · Suite:
`uml/tests/test_conformance.py` (10 structural facts, see
[CONTRACT.md](CONTRACT.md)) · pytest 9.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 entities share a common `Entity` base | P | P | P | P |
| U2 `Task --|> Entity` | P | P | P | P |
| U3 `Section --|> Entity` | P | P | P | P |
| U4 `Section --> Task` (`tasks`) | P | P | P | P |
| U5 `Section --> Section` (`subsections`) | P | P | P | P |
| U6 `Task --> Attachment` (`attachments`) | P | P | P | P |
| U7 `Task --> RecurrenceInfo` (`recurrence`) | P | P | P | P |
| U8 Task lifecycle method set | P | P | P | P |
| U9 Task attachment methods | P | P | P | P |
| U10 Section membership method set | P | P | P | P |
| **Pass / 10** | 10 | 10 | 10 | 10 |
| **Score** | 1.000 | 1.000 | 1.000 | 1.000 |

Run summary: **40 passed, 0 failed, 0 N/A.**

## How the structure diverged

It did not. The domain-layer UML structure is reproduced with **perfect
fidelity** by all four generations. Every generation redefines the full
`Entity` hierarchy (`Task`/`Section`/`User`/`RecurrenceInfo`/`Attachment` all
subclassing a shared `Entity`), keeps the four domain associations typed with
their real target classes on the *domain* `Task`/`Section` (even where the
parallel ORM `TaskModel`/`SectionModel` widen `tasks`/`attachments` to `Any` —
`uml/gpt`), and carries the complete `Task` lifecycle/attachment and `Section`
membership method sets. Implementation style varies (pydantic models in
claude/deepseek/gemini, dataclasses in gpt) but the structure the diagram
records is identical.

## Classification

- **No F, no N/A.** The class-diagram contract is unambiguous and the four
  generations all satisfied it. The set/superset method checks tolerate extra
  members (each generation adds more), so the passes are genuine rather than
  vacuous.

## Reproduce

```bash
cd repos/m-danya__planty/uml/tests
python3 -m pytest -p no:warnings -q        # full matrix
```
