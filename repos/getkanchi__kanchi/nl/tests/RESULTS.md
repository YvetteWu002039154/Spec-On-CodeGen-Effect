# Conformance results — `Kanchi` **NL track**

Suite:
`nl/tests/test_conformance.py` (8 behaviors N1–N8 + 2 dependency checks, in [CONTRACT.md](CONTRACT.md)).
- `pass` = matches the contract ·
- `FAIL` = capability wrong, **not exposed**, or named package **not used**.

## Matrix

| check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  task-state vocabulary (success/failure/retry) | pass | pass | **FAIL** | **FAIL** |
| N2  task retry counter | pass | pass | pass | pass |
| N3  orphan detection | pass | pass | pass | pass |
| N4  daily-statistics succeeded/failed counts | pass | pass | pass | pass |
| N5  statistics accumulation increments success | pass | pass | pass | pass |
| N6  worker health status + heartbeat | pass | pass | pass | pass |
| N7  connection disconnect removes + idempotent | pass | pass | pass | pass |
| N8  auto-migration runner | pass | pass | pass | pass |
| dep `celery` used | FAIL | FAIL | pass | pass |
| dep `alembic` used | FAIL | FAIL | FAIL | pass |
| **Pass / 10** | **8** | **8** | **8** | **9** |

**Total:** 33 passed, 7 failed (40 checks).

## The failures

- **N1** (deepseek, gemini) — task state is carried as **free strings** (a
  `String` `status`/`state` column and string literals like
  `'SUCCESS'`/`'FAILURE'`/`'RETRY'`), with **no enumerable state vocabulary**.
- **dep `celery`** (claude, gpt) — monitor a hand-rolled task model instead of
  wiring a `Celery` app; deepseek and gemini use it.
- **dep `alembic`** (claude, gpt, deepseek) — create tables directly instead of
  running Alembic migrations; only gemini uses the named migration tool.

Dependency checks are static AST checks (`loader.dependency_used`): `pass` =
imports and references the package; `FAIL` = absent or a dead import.

## Reproduce

```bash
cd repos/getkanchi__kanchi/nl/tests
python3 -m pytest -q -p no:warnings
```
