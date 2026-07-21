# Conformance results — `pydantic-ai-todo` **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
Each is driven by its own explicit driver in `adapter.py`. `pass` = behavior
matches the contract · `FAIL` = capability wrong or genuinely broken when driven
(this suite does not skip / mark N/A). There is no reference in the NL track
(behavioral). See [CONTRACT.md](CONTRACT.md).

**Infra-dependent generations.** Two of the four expose *only* a PostgreSQL
backend with no in-memory path: deepseek's `TodoToolset(tenant_id, pool)` runs
over an `asyncpg` pool, gemini's `TodoToolset(db_dsn)` over a psycopg2 DSN. To
score them on **behavior** rather than on infrastructure availability, the suite
stands up a throwaway PostgreSQL (pip-installable `pgserver`, no system deps —
see [`_dbharness.py`](_dbharness.py)) and gives each test its own fresh, empty
database. deepseek receives a loop-safe pool substitute whose `.acquire()` opens
a connection in the current event loop (a real `asyncpg` pool is bound to one
loop and cannot survive the adapter's per-call `asyncio.run(...)`); gemini
receives the fresh database's DSN, and its constructor's `CREATE TABLE` runs for
real. The harness also calls `psycopg2.extras.register_uuid()` — the standard,
process-global psycopg2 setup for `uuid` columns that an application normally
does once at startup — so gemini's SQL, which binds `uuid.UUID` parameters, is
exercised on its real logic rather than blocked by the adapter's absence.

**Methodology note:** this credits DB-backed generations that are actually
correct (environment provisioning only — no generation's source is modified),
but it is *not* applied uniformly across the corpus: other repos' infra-dependent
generations are still scored as-is. Treat it as a vstorm-specific fairness
adjustment when comparing tracks.

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  add task observable | pass | pass | FAIL | pass |
| N2  list all tasks | pass | pass | FAIL | pass |
| N3  update status by id | pass | pass | FAIL | pass |
| N4  delete by id | pass | pass | FAIL | pass |
| N5  create child task | pass | pass | FAIL | pass |
| N6  link dependency | pass | pass | FAIL | pass |
| N7  ready reflects dependency | pass | pass | FAIL | pass |
| N8  bulk write | pass | pass | FAIL | pass |
| N9  hierarchical view | pass | pass | FAIL | pass |
| **Pass / 9** | **9** | **9** | **0** | **9** |

**Totals: 27 passed, 9 failed.**

N6 is observed by *effect* (linking `b`→`a` with `a` incomplete moves `b` from the
ready list to blocked), not by the link method's return value — see "N6
observation" below.

## Interpretation

- **claude** and **gpt** both ship an in-memory backend (claude's async
  `TodoToolset` defaults to an `InMemoryStorage`; gpt's takes an injected
  `InMemoryTaskStorage`), so all nine behaviors are drivable and correct —
  including the discriminating **N7**, where a task linked to an incomplete
  dependency is excluded from the ready list and only becomes ready after the
  dependency is completed.

- **gemini (9/9).** Against a real database with UUID adaptation registered,
  gemini's storage is correct on every behaviour, including the discriminating
  **N7**. Its earlier lone miss on **N6** was an observation artefact, not a
  defect: gemini's `link_tasks` records the dependency (it calls `add_dependency`
  and **N7 drives the same method**) but returns `None`, so the old return-value
  check read it as failure. N6 now observes the *effect* — after linking, `b`
  leaves the ready list — and gemini passes. Its only remaining miss is the
  static `pydantic_ai` dependency check, which all four generations fail.

- **deepseek (0/9).** Driven against the same real database, deepseek fails every
  behaviour — but on a **single blocking defect**, not nine independent ones.
  After a successful `INSERT ... RETURNING`, it calls `Task.model_validate(row)`
  on the raw `asyncpg` Record while its `Task` model sets `from_attributes=True`;
  pydantic then reads fields by *attribute* (`row.id`), which a Record does not
  support (only mapping access), so it recovers nothing and raises
  `pydantic ValidationError: 3 validation errors for Task` (the three
  required-no-default fields `id, tenant_id, title`), wrapped as
  `RuntimeError("Failed to insert task")`. The correct code is
  `Task.model_validate(dict(row))`. Because every read and write path shares this
  one line, no behaviour can return a `Task`. The diagnostic
  `test_deepseek_failures_share_one_blocking_bug` (un-parameterised, so excluded
  from pass@1) confirms the storage layer works: the row **is** persisted; only
  the return-marshalling raises. So deepseek's 0/9 is *blocked by one bug*, not
  *nine-times wrong* — a distinction worth carrying into any aggregate.

## N6 observation — by effect, not return value

N6 ("link dependency") is observed behaviourally: each driver adds two tasks,
confirms `b` is initially ready, links `b`→`a` (with `a` incomplete), and
requires `b` to have left the ready list. This tests that the dependency was
*recorded and takes effect*, independent of whether the generation's `link_*`
method returns a confirmation value. The rule is applied identically to all four
generations (deepseek still FAILs — it cannot add a task in the first place). An
earlier return-value check scored gemini's void-returning `link_tasks` as FAIL
even though the dependency was recorded; the effect-based check corrects that
false negative without crediting any behaviour that does not actually work.

## Divergences worth noting (do not affect the contract)

The driveable generations diverge from the origin's status vocabulary — claude
uses `pending/in_progress/completed/blocked/cancelled`, gpt uses
`todo/in_progress/blocked/done/canceled`. The drivers name each generation's own
enum member (`IN_PROGRESS`; `COMPLETED`/`DONE` for completion) so this vocabulary
drift does not cause spurious failures.

## Reproduce

```bash
cd thesis_repos/vstorm-co__pydantic-ai-todo/nl/tests
python3 -m pytest -q
```

The deepseek/gemini tracks require `pgserver` (in `requirements.txt`); it starts
one throwaway PostgreSQL for the session and cleans it up at exit. No system
PostgreSQL is needed.

## Dependency usage

Complementary to the behavior matrix above: does each generation **import
and use the package(s) the description names** (static AST check,
`loader.dependency_used`), or hand-roll a substitute? `pass` = imports and
references the package · `FAIL` = does not use it (absent, or a dead import).

| dependency | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| `pydantic_ai` | FAIL | FAIL | FAIL | FAIL |

**None** of the four actually use `pydantic_ai`. claude imports `Agent`/`Tool` under a `try/except` but never references them (a **dead import**, which the AST check rejects); gpt, deepseek and gemini do not import it at all — they expose a plain toolset without the named agent framework.
