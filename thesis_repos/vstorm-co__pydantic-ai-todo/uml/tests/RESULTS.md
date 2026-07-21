# Conformance results — `pydantic-ai-todo` **UML track**

Reference: origin package `pydantic-ai-todo-main/pydantic_ai_todo/` · Suite:
`uml/tests/test_conformance.py` (10 structural facts, see
[CONTRACT.md](CONTRACT.md)) · pytest 9.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 `TodoEventType --* TodoEvent` | P | P | P | P |
| U2 `Todo --* TodoEvent` | P | P | P | P |
| U3 `Todo` fields | P | P | P | P |
| U4 `TodoItem` fields | P | P | P | P |
| U5 `TodoStatusUpdate` fields | P | P | P | P |
| U6 `AsyncMemoryStorage` CRUD | P | P | P | P |
| U7 `AsyncPostgresStorage` + lifecycle | P | P | P | F |
| U8 `AsyncRedisStorage` + lifecycle | P | P | P | F |
| U9 `TodoEventEmitter` method set | P | P | P | P |
| U10 `TodoCapability` method set | F | F | P | F |
| **Pass / 10** | 9 | 9 | 10 | 7 |
| **Score** | 0.900 | 0.900 | 1.000 | 0.700 |

Run summary: **35 passed, 5 failed, 0 N/A.**

## Interpretation

The class *roster* and data-model structure are reproduced by all four
generations — the full class list (`Todo`, `TodoItem`, `TodoStatusUpdate`,
`TodoEventType`, `TodoEvent`, `TodoEventEmitter`, the four storage classes, and
`TodoCapability`), the two composition links (`TodoEvent.event_type:
TodoEventType`, `TodoEvent.todo: Todo`), the six `Todo`/`TodoItem` fields (U1–U6,
U9 all pass). The divergence appears in the **method-set facts**, which now
require a real (non-stub) body:

- **U10 `TodoCapability` — F for `cla`/`gpt`/`gem`.** All three leave
  `get_toolset` (and, in `gpt`, `get_instructions`) as `return None`, so the
  capability's drawn operations are judged not implemented. Only `uml/deepseek`
  gives them real bodies.
- **U7/U8 — F for `gemini`.** `AsyncPostgresStorage` and `AsyncRedisStorage`
  emit `initialize`/`close` as a bare `pass`, dropping the persistent-backend
  lifecycle the diagram draws.
- `uml/deepseek` is the only clean sweep (10/10).

This compounds the **NL (behavioral) track**, where the same four generations
diverged hard on *architecture* (in-memory vs. DB-only): the class roster
transferred easily, but the operations behind it — persistence lifecycle and the
capability toolset — were often left as placeholders.

## Reproduce

```bash
cd thesis_repos/vstorm-co__pydantic-ai-todo/uml/tests
python3 -m pytest -v                # full matrix
```
