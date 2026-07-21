# Conformance results — `NexusCtrl` **UML track**

Reference: origin repo `NexusCtrl-main/backend/app.py`

## Matrix (P = pass, F = fail)

| Behavior | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 entities share a common base | P | P | P | P |
| U2 TaskCreate ➝ TaskBase | P | P | P | P |
| U3 TaskResponse ➝ TaskBase | P | P | P | P |
| U4 TaskBase → TaskPriority | P | **F** | P | P |
| U5 TaskBase → TaskStatus | P | **F** | P | P |
| U6 TokenResponse → UserResponse | P | P | P | P |
| U7 manager full method set | P | P | P | P |
| U8 manager client connect/disconnect | P | P | P | P |
| U9 manager agent connect/disconnect | P | P | P | P |
| U10 manager broadcast_to_clients | P | P | P | P |
| **Pass / 10** | 10 | 8 | 10 | 10 |
| **Score** | 1.000 | 0.800 | 1.000 | 1.000 |

Run summary: **38 passed, 2 failed, 0 skipped.**

## How the structure diverged

The only divergence:

- **`uml/gpt` drops the two `TaskBase` association types.** Where the diagram
  draws `TaskBase --> TaskPriority` and `TaskBase --> TaskStatus`, `uml/gpt`
  annotates `priority: Any` and `status: Any` — the attributes exist but no longer
  reference the enum types, so the modelled associations are lost (U4, U5 → F). It
  still keeps the `TaskBase` **base** intact, so `TaskCreate`/`TaskResponse` and
  `TokenResponse --> UserResponse` pass. (Its `TaskUpdate` — not under test — does
  use `Optional[TaskPriority]`, so the enums exist; only the `TaskBase` fields were
  widened to `Any`.)

## Reproduce

```bash
cd thesis_repos/Twiddllo__NexusCtrl
python3 -m pytest uml/tests/test_conformance.py -p no:warnings -q # full matrix
```
