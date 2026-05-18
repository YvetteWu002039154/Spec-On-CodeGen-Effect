# Behavior Test Specification
## NexusCtrl — Correctness Evaluation

**Ground truth:** `thesis_repos/NexusCtrl/NexusCtrl-main/backend/app.py`  
**Evaluated codes:** `./{condition}/outputcode/{model}/generated_code.py`  
**Conditions:** `uml` (4 models), `nl` (4 models)  
**Models:** `claude`, `gpt`, `gemini`, `deepseek`

---

## Test Suite Overview

Both NL and UML conditions are evaluated against the **same 12 behavioral checks** derived from `app.py`. Tests are interface-adapted per model (different class names, attribute naming conventions, dataclass vs ORM) but verify identical behaviors.

Adaptation rules applied across all 8 test files:
- `TaskPriority` → also accepts `Priority` (gpt NL)
- `MetricSnapshot` → also accepts `SystemMetrics` (claude/gpt NL) or `Metrics` (gemini NL)
- `Server` → also accepts `ServerConfig` (claude NL) or `ServerState` (deepseek NL)
- Attribute checks use `hasattr` **and** `__dataclass_fields__` to handle both ORM Column descriptors and plain dataclass fields
- T03: accepts `"pending"` alongside `"todo"`, and `"completed"` alongside `"done"`
- T08: accepts `host`, `addr`, `ip_address` alongside `hostname`
- T09: accepts `description` alongside `title`; accepts `server_id` or `assigned_server` alongside `project_id`

---

## Test Suite (T01–T12) — Same for Both Conditions

### T01 — ServerStatus has 'online' value
**Source:** `ServerStatus.ONLINE = "online"`  
**Assert:** `"online" in {s.value for s in ServerStatus}`

### T02 — ServerStatus has 'offline' value
**Source:** `ServerStatus.OFFLINE = "offline"`  
**Assert:** `"offline" in {s.value for s in ServerStatus}`

### T03 — TaskStatus has a pending/todo and done/completed value
**Source:** `TaskStatus.TODO = "todo"`, `TaskStatus.DONE = "done"`  
**Assert:** `"todo" or "pending"` in values; `"done" or "completed"` in values

### T04 — TaskPriority has all four ground-truth levels
**Source:** `TaskPriority.LOW/MEDIUM/HIGH/CRITICAL`  
**Assert:** `"low"`, `"medium"`, `"high"`, `"critical"` all present as string values

### T05 — User model has username and email
**Source:** `User.username`, `User.email` columns  
**Assert:** User class defined; has `username`/`name` and `email`

### T06 — User has hashed_password and is_active
**Source:** `User.hashed_password`, `User.is_active` columns  
**Assert:** User class defined; has `hashed_password`/`password` and `is_active`/`active`

### T07 — Project has name and owner_id
**Source:** `Project.name`, `Project.owner_id` columns  
**Assert:** Project class defined; has `name` and `owner_id`/`owner`

### T08 — Server has hostname and status
**Source:** `Server.hostname`, `Server.status` columns  
**Assert:** Server class defined; has `hostname`/`host`/`addr`/`ip_address` and `status`/`online`

### T09 — Task has title and a project/server reference
**Source:** `Task.title`, `Task.project_id` columns  
**Assert:** Task class defined; has `title`/`description` and `project_id`/`server_id`/`assigned_server`

### T10 — MetricSnapshot has cpu_percent
**Source:** `MetricSnapshot.cpu_percent` column  
**Assert:** MetricSnapshot/SystemMetrics/Metrics class defined; has `cpu_percent`

### T11 — MetricsConnectionManager can be instantiated
**Source:** `class MetricsConnectionManager`  
**Assert:** class defined; `MetricsConnectionManager()` does not raise

### T12 — UserRole has 'admin' value
**Source:** `UserRole.ADMIN = "admin"`  
**Assert:** UserRole defined; `"admin" in {r.value for r in UserRole}`

---

## Actual Results

| Test | uml/claude | uml/deepseek | uml/gemini | uml/gpt | nl/claude | nl/deepseek | nl/gemini | nl/gpt |
|------|:----------:|:------------:|:----------:|:-------:|:---------:|:-----------:|:---------:|:------:|
| T01  | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS |
| T02  | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS |
| T03  | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| T04  | PASS | **FAIL** | **FAIL** | **FAIL** | PASS | **FAIL** | PASS | PASS |
| T05  | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| T06  | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| T07  | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| T08  | PASS | PASS | PASS | **FAIL** | **FAIL** | PASS | **FAIL** | **FAIL** |
| T09  | PASS | PASS | PASS | **FAIL** | PASS | PASS | **FAIL** | **FAIL** |
| T10  | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | **FAIL** |
| T11  | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| T12  | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **Score** | **12/12** | **11/12** | **11/12** | **9/12** | **6/12** | **1/12** | **5/12** | **5/12** |

---

## pass@1 Rates

| Condition/Model | Passed | pass@1 rate | strict pass@1 |
|---|:---:|:---:|:---:|
| uml/claude | 12/12 | 1.0000 | 1 |
| uml/deepseek | 11/12 | 0.9167 | 0 |
| uml/gemini | 11/12 | 0.9167 | 0 |
| uml/gpt | 9/12 | 0.7500 | 0 |
| nl/claude | 6/12 | 0.5000 | 0 |
| nl/deepseek | 1/12 | 0.0833 | 0 |
| nl/gemini | 5/12 | 0.4167 | 0 |
| nl/gpt | 5/12 | 0.4167 | 0 |

---

## Key Findings

- **UML avg:** (12 + 11 + 11 + 9) / 48 = **89.6%**
- **NL avg:** (6 + 1 + 5 + 5) / 48 = **35.4%**
- UML condition strongly outperforms NL: the class diagram explicitly encodes the backend data model (User, Project, Server, Task ORM, UserRole, MetricsConnectionManager), so all 4 UML codes implement the required structure. NL models interpreted the description as a monitoring desktop tool and missed the backend layer entirely.
- T05–T07, T11, T12 fail for **all 4 NL codes** — User, Project, UserRole, and MetricsConnectionManager are absent in every NL-generated implementation.
- nl/deepseek scores 1/12 (only T03) — uniquely fails T01/T02 (no ServerStatus enum) and T04 (TaskPriority uses integer values 1–4, not strings).
- uml/gpt fails T08 and T09 — its Server and Task use private instance attributes (`_hostname`, `_title`) rather than ORM Column descriptors or dataclass fields, so the attribute check does not find them.
- uml/deepseek and uml/gemini fail T04 — missing one TaskPriority level in their generated enum.

---

## pass@k Definition

For each model/condition pair (one generated sample), **pass@1** is computed in two ways:

1. **Test pass rate** (continuous): `c / n` where `c` = tests passed, `n` = 12 total tests.
2. **Strict pass@1** (binary): `1` if all 12 tests pass, else `0`.

For multiple samples (if re-run at different temperatures), the unbiased estimator is:

```
pass@k = 1 - C(n - c, k) / C(n, k)
```

where `n` = total samples, `c` = samples passing all tests, `k` = the k value.
