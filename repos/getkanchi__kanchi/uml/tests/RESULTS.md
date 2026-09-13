# Conformance results — `Kanchi` **UML track**

Grounding: origin `kanchi-main/agent/` · Suite: `uml/tests/test_conformance.py`
(10 structural facts, U1–U10 in [CONTRACT.md](CONTRACT.md)) · pytest 9,
Python 3.12.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1  `RetryActionHandler → ActionHandler` | P | P | P | P |
| U2  `SlackActionHandler → ActionHandler` | P | P | P | P |
| U3  `ActionHandler` method set | P | P | P | P |
| U4  `RetryActionHandler` overrides | P | P | P | P |
| U5  `SlackActionHandler` overrides | P | P | P | P |
| U6  `ConnectionManager` method set | P | P | P | P |
| U7  `CeleryEventMonitor` method set | P | P | **F** | P |
| U8  `EventHandler` method set | P | P | **F** | **F** |
| U9  `DatabaseManager` method set | P | P | **F** | P |
| U10 `EnvironmentDB.to_dict()` | P | P | P | P |
| **Pass / 10** | 10 | 10 | 7 | 9 |
| **Score** | 1.000 | 1.000 | 0.700 | 0.900 |

Run summary: **36 passed, 4 failed, 0 N/A.**

## Interpretation

The class **skeleton** — every contracted class, its inheritance family, and the
*names* of the operations the diagram draws — is reproduced by all four
generations. Where they diverge is whether those operations are **real
definitions or placeholders**, which the strengthened (non-stub) check now
surfaces:

- **`uml/claude`, `uml/gpt` — 10/10.** Every drawn operation is a substantive
  definition.
- **`uml/gemini` — 9/10.** Fails **U8**: `EventHandler.handle_steps_event` is a
  bare `# Business logic for steps event` comment followed by `pass` (the other
  three dispatchers do real work). One of four contracted operations is a stub,
  so the method-set fact is not met.
- **`uml/deepseek` — 7/10.** Fails **U7** (`CeleryEventMonitor.start_monitoring`
  and `stop` are `pass`), **U8** (all four `handle_*_event` are `pass`), and
  **U9** (`DatabaseManager.run_migrations` is `pass`). The classes and method
  names are all present, but the monitor lifecycle, the entire event-dispatch
  surface, and migration entry point are empty placeholders.

The two inheritance facts and both **override** facts (U4/U5) hold for every
generation: each defines `RetryActionHandler`/`SlackActionHandler` as proper
subclasses of `ActionHandler` and gives both a concrete, directly-defined
`execute` + `validate_params` — not an inherited or still-abstract one.

**Takeaway.** A presence-only structural check reports 40/40 here — every class
and method *name* matches the diagram. Requiring the drawn operations to be
non-stub separates that surface match from actual substance: deepseek and gemini
ship EventHandlers (and, for deepseek, a monitor and migration hook) that satisfy
the diagram's shape while doing nothing. This is the structural analogue of the
behavioral divergence the NL track found — a class diagram is an easy target to
hit by name, and hitting it by name is not the same as filling it in.

## Reproduce

```bash
cd repos/getkanchi__kanchi/uml/tests
python3 -m pytest -v -p no:warnings                 # full matrix
python3 -m pytest -k deepseek -q                    # the 3 stub failures
```
