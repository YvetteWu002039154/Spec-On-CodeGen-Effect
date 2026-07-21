# Conformance results — `asimov` (BismuthCloud) **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
Grounding: the **NL description** (`nl/input/description.txt`) Caching System
clause. Suite: `nl/tests/test_conformance.py` (11 behaviors, see
[CONTRACT.md](CONTRACT.md)).

Each generation is driven by its own explicit driver in `adapter.py` that names
the concrete Cache class and calls **that generation's real API**. `pass` =
described capability exhibited · `FAIL` = capability cannot be exhibited through
any API the generation exposes. Conformance is judged against the description,
not against the origin's method surface (see CONTRACT.md § "Conformance
philosophy").

## Matrix

| Behavior | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  set/get round-trip | pass | pass | pass | pass |
| N2  missing key → `None` | pass | pass | pass | pass |
| N3  `get` returns a fresh object (JSON) | pass | pass | pass | pass |
| N4  `set` overwrites | pass | pass | pass | pass |
| N5  `delete` removes a key | pass | pass | pass | pass |
| N6  `clear` empties | pass | pass | pass | pass |
| N7  `get_all` mapping | pass | pass | pass | pass |
| N8  prefix round-trip | pass | pass | pass | pass |
| N9  prefix isolation | pass | pass | pass | pass |
| N10 mailbox FIFO (deliver-if-listening) | pass | pass | pass | pass |
| N11 empty mailbox → `None` | pass | pass | pass | pass |
| **Pass / 11** | 11 | 11 | 11 | 11 |

**Totals:** 44 passed, 0 failed (44 cells = 11 behaviors × 4 generations).

## Notes

- All four generations fulfill the description's Caching System clause. They
  differ in **API shape**, which the driver absorbs per-generation:
  - **Namespacing** — gpt exposes `with_namespace(prefix=…)`; claude, deepseek,
    and gemini namespace via constructor `prefix`/`suffix`. Both are driven
    through the respective real API and give genuine prefix round-trip + isolation.
  - **Mailboxes** — claude/gemini expose a `subscribe()` async generator, gpt a
    `mailbox(name)` object, deepseek `subscribe(channel, callback)`. All are pub/sub
    (deliver-if-listening), so the driver subscribes before publishing.
  - **Serialization** — every generation JSON-(de)serializes values (claude is
    driven through its `RedisCache`, which serializes, not `InMemoryCache`), so
    `get` yields a fresh object and N3 holds for all four.
- Behaviors the description does **not** name are not pinned, so they are not
  scored: a `keys()` method (bulk ops in the description are `get_all`/`clear`),
  and missing-key semantics beyond returning `None` (no `KeyError`/default
  contract). Earlier revisions of this suite scored those against the origin API
  and reported them as failures; they have been removed as over-specified
  relative to the description.

## Reproduce

```bash
cd thesis_repos/BismuthCloud__asimov/nl/tests
python3 -m pytest -p no:warnings -q
```
