# POC-v1 — Thesis Evaluation Pipeline

End-to-end pipeline for comparing LLM code generation quality from natural-language (NL) and UML specifications, measured via pass@1, SonarQube internal quality, and human rating.

**Scope of the dataset:** 12 repos × 2 conditions (NL, UML) × 4 models × 10 generations = **960 generations**.

---

## Repository Layout

```
POC-v1/
├── step0_search_repos.py        ← Search GitHub for candidate repos by quality
├── step1_repo_pipeline.py       ← Download repo zip & scaffold folder structure
├── step2_code_generation.py     ← Call LLMs to generate code from NL / UML inputs
├── step3_functional_correctness.py ← NL: run behavioural suite, pass@1 (run0 only)
├── step3_structural_fidelity.py    ← UML: run structural suite, pooled over 10 runs
├── step3_common.py                 ← shared internals for both (library, no CLI)
├── step4_sonarqube.py           ← Run SonarQube analysis on all 10 runs per cell
├── step5_build_db.py            ← Consolidate all per-repo results (+ human eval) into SQLite
├── results.db                   ← SQLite dataset written by step5 (tracked) — tables:
│                                    generation_runs, test_results, sonar_results,
│                                    human_evaluation (rebuilt by step5), plus
│                                    repos, variance_pilot, human_eval_selection
│                                    (written out-of-band, left untouched by step5)
├── schema/                      ← One `CREATE TABLE` per file; step5 reads these
│   └── <table>.sql                 rather than embedding DDL in Python
├── adapter_harness/             ← Shared import-time machinery for the NL suites
│   ├── permissive_stubs.py      ← `_PermissiveModule` — lets a generation that
│   │                               imports an uninstalled optional top still exec
│   └── faketk.py                ← tkinter stand-in: constructs without a display
│                                   and captures widget callbacks, so closure-based
│                                   persistence logic can be exercised headlessly
├── Human Evaluation Reports/    ← Manually-scored human evaluation
│   ├── <owner>__<repo>/         ← one markdown rating form per rated generation:
│   │   └── <repo>_<NL|UML>_<Model>.md   readability, maintainability, proximity rank
│   └── human_evaluation.csv     ← the forms' scores transcribed into one long-format
│                                    CSV (repo, condition, model, metric, score) — the
│                                    file step5 actually reads
├── Reports/
│   ├── analysis.ipynb           ← Statistical analysis; writes human_eval_selection.csv
│   ├── data_collection.json     ← 125-entry provenance log of the collection process
│   ├── human_eval_selection.csv ← the 24 cells where a non-run0 generation was rated
│   ├── failure_analysis.md      ← failing-test write-up (gitignored, local scratch)
│   └── variance_pilot/          ← Run-to-run variance pilot (writes the
│       ├── functional_correctness.py     `variance_pilot` table in results.db)
│       ├── structural_fidelity.py
│       └── <owner>__<repo>/     ← the pilot's own copy of a suite, driven by
│                                   `adapter_per_run.py` instead of the main
│                                   study's single-generation adapter
├── utils/
│   ├── check_size_thresholds.py ← Check method/class size thresholds across generations
│   └── count_uml_classes.py     ← Count class declarations in each repo's UML diagram
├── repos/                       ← One folder per evaluated repo. The ground-truth
│   └── <owner>__<repo>/            source clone (`<repo>-main/`) is gitignored and no
│       │                           longer on disk — see the `repos` table for URLs.
│       ├── results.json             ← Step 3 output (per condition/model)
│       ├── sonar_results.json       ← Step 4 output (per condition/model/run)
│       ├── nl/
│       │   ├── input/
│       │   │   └── description.txt      ← NL specification (written manually)
│       │   ├── outputcode/
│       │   │   ├── <model>.run<N>.py            ← N = 0..9, one per generation
│       │   │   └── <model>.run<N>.metadata.json ← model, tokens, latency, timestamp, code
│       │   └── tests/                   ← NL behavioral conformance suite
│       │       ├── CONTRACT.md          ← behaviors pinned (Nn) + origin grounding
│       │       ├── loader.py            ← loads a generation (real libs, stubs missing)
│       │       ├── adapter.py           ← one interface over each generation (by behavior)
│       │       └── test_conformance.py  ← shared test body, parametrized over the 4 models
│       └── uml/
│           ├── input/
│           │   └── classes.puml         ← PlantUML class diagram (written manually)
│           ├── outputcode/
│           │   ├── <model>.run<N>.py            ← N = 0..9, one per generation
│           │   └── <model>.run<N>.metadata.json
│           └── tests/                   ← UML structural conformance suite
│               ├── CONTRACT.md          ← facts pinned (Un) + origin grounding
│               ├── loader.py            ← loads a generation (stubs heavy deps)
│               ├── structure.py         ← reflection helpers over the loaded module
│               └── test_conformance.py  ← shared test body, parametrized over the 4 models
├── .env                         ← API keys + SONAR_TOKEN (never commit)
├── .env.example
├── requirements.txt             ← pinned direct dependencies, grouped by step
├── requirements.lock.txt        ← full transitive freeze of the working environment
└── README.md
```

A suite may carry extra fixture files alongside the four core ones (e.g. `nl/tests/library.json`) when its contract needs seed data.

---

## Models

| Key | Model |
|---|---|
| `claude` | Claude Sonnet 4.6 |
| `gpt` | GPT-5.2 |
| `gemini` | Gemini 3.1 Pro |
| `deepseek` | DeepSeek V4-Pro |

---

## Six-Step Workflow

### Step 0 — Find Candidate Repos

Searches GitHub for Python OOP projects matching predefined queries (library systems, banking systems, etc.). Filters candidates by star count and README quality, then prints a ranked list for manual review. No cloning, no LLM calls — discovery only.

```bash
python step0_search_repos.py
python step0_search_repos.py --max-results 20
python step0_search_repos.py --min-stars 20 --max-stars 200
```

| Flag | Default | Description |
|---|---|---|
| `--max-results N` | 50 | Number of repos to return per query |
| `--min-stars N` | 1 | Minimum GitHub stars |
| `--max-stars N` | 1000 | Maximum GitHub stars |

Required in `.env`:
```
GITHUB_TOKEN=...  (optional but recommended for higher API rate limits)
```

---

### Step 1 — Download Repo & Scaffold

Downloads a GitHub repo as a zip and extracts it into `repos/<owner>__<repo>/<repo>-main/`. Also creates the full folder scaffold (`nl/input/`, `nl/outputcode/`, `nl/tests/`, `uml/input/`, `uml/outputcode/`, `uml/tests/`).

```bash
python step1_repo_pipeline.py --repo https://github.com/ecopque/new_banking_system
python step1_repo_pipeline.py --repo ecopque/new_banking_system
```

`<repo>-main/` is gitignored — it is ground-truth reference material for authoring the specs and contracts, never an evaluated row. The 12 already-scored repos have had theirs deleted to save space; re-download with this step if you need to consult one.

After Step 1, manually create the inputs:
- `repos/<owner>__<repo>/nl/input/description.txt` — natural language description of the system
- `repos/<owner>__<repo>/uml/input/classes.puml` — PlantUML class diagram

#### Generating `classes.puml` with pyreverse

```bash
pip install pylint
cd repos/<owner>__<repo>/<repo>-main/
pyreverse -o puml -p ProjectName path/to/models.py path/to/other_modules/
mv classes.puml ../uml/input/classes.puml
```

You can preview `.puml` files in VS Code with the PlantUML extension.

---

### Step 2 — LLM Code Generation

Reads the NL description and/or UML diagram for each repo and calls all configured LLMs. Writes one file pair per **(condition, model, run)**.

```bash
# All repos, both conditions, all models, 1 run (run0)
python step2_code_generation.py

# The study's actual sampling: 10 generations per cell
python step2_code_generation.py --runs 10

# Fill only the runs that are missing or previously failed
python step2_code_generation.py --runs 10 --skip-existing
python step2_code_generation.py --run-index 3 5 --skip-existing

# Narrow the scope
python step2_code_generation.py --repo ecopque__new_banking_system --condition nl --models claude gpt
```

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `repos/` |
| `--condition` | `both` | `nl`, `uml`, or `both` |
| `--models` | all | One or more of: `claude gpt gemini deepseek` |
| `--runs N` | 1 | Generate N runs per cell, indexed `0..N-1` |
| `--run-index K [K …]` | — | Generate only these run indices; overrides `--runs` |
| `--skip-existing` | off | Skip `(condition, model, run)` triples whose `.run<N>.py` already exists |
| `--timeout N` | 600 | Per-request timeout, seconds |
| `--max-retries N` | 2 | Retries on transient API errors, exponential backoff |

Output per (condition, model, run):
- `<condition>/outputcode/<model>.run<N>.py` — generated implementation
- `<condition>/outputcode/<model>.run<N>.metadata.json` — the durable per-generation record: `model` (display name), `output_tokens`, `latency_s`, `generated_at`, and the generated `code`. This is what Step 5 reads, so regenerating one cell never clobbers the others' records.

A model that ignores the "single file" instruction may instead deliver a project tree at `<condition>/outputcode/<model>.run<N>/`. Steps 3 and 4 both handle that shape.

Required in `.env`:
```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
```

---

### Step 3 — Correctness Evaluation (pass@1)

Runs the per-track **conformance suite** under each repo's `nl/tests/` and `uml/tests/` with `pytest` (one subprocess per track per run), parses the JUnit XML, groups test cases by the implementation each one exercises, and merges results into `repos/<repo>/results.json`.

Each track ships **one** shared `test_conformance.py`, parametrized over that track's **4 generated implementations only** (ids like `nl/claude`, `uml/gpt`) — **there is no `reference` row**. Both tracks evaluate the four generations against a contract authored from the ground-truth source; the original repo's source is not run as a row.

**Prerequisite:** install the dependencies first — the suites import the same runtime libraries the generated code uses (`pytest`, `Django`, `fastapi`, `SQLAlchemy`, …):

```bash
pip install -r requirements.txt
```

```bash
python step3_functional_correctness.py    # NL
python step3_structural_fidelity.py       # UML
```

Neither script takes arguments: each scores every repo that has a suite for its track, across all models. The UML scorer scores `RUNS = 10` generations per cell and pools their counts; the NL scorer scores run0 only.

A test outcome is one of three, and **skips are reported separately from failures**: a *skip* means the implementation lacks that capability/structure entirely (the adapter raised `Unsupported`, reported as **N/A**), whereas a *failure* means the capability exists but behaves or is shaped wrongly.

#### Running a suite directly with pytest

Step 3 discards pytest's own output on success ([step3_common.py:107-112](step3_common.py#L107-L112) deletes its temp files in `finally`), so when you want to see *why* something fails — tracebacks, captured stdout, one line per test — invoke pytest yourself:

```bash
# One repo, one track — verbose, one line per (test, model)
python3 -m pytest repos/ecopque__new_banking_system/nl/tests -v

# Just the counts
python3 -m pytest repos/ecopque__new_banking_system/nl/tests -q

# One model only (the parametrize id is the impl id)
python3 -m pytest repos/ecopque__new_banking_system/nl/tests -v -k "nl/claude"

# Full tracebacks
python3 -m pytest repos/ecopque__new_banking_system/uml/tests -vv --tb=long
```

Output looks like this — the bracket is the impl id that [step3_common.py:28-33](step3_common.py#L28-L33) parses to attribute each case to a model:

```
test_deposit_increases_balance[nl/claude]      PASSED
test_withdraw_zero_or_negative[nl/claude]      FAILED
test_deposit_increases_balance[nl/gpt]         PASSED
```

**Choosing which generation runs.** Because each cell has 10 generations, the suite picks one via the `RUN` environment variable rather than by moving files around:

```bash
RUN=3 python3 -m pytest repos/<repo>/uml/tests -v
```

⚠️ **`RUN` is honored by the UML loaders only.** All 12 NL loaders hardcode the path (`f"{model}.run0.py"`), so on the NL track `RUN` is silently ignored and run0 is always scored — which is also why `step3_functional_correctness.py` reports run0 only. Setting `RUN=3` on an NL suite does not error; it just scores run0 anyway. Per-run NL numbers currently come from `Reports/variance_pilot/`, whose copy of the suite uses `adapter_per_run.py` to select the generation explicitly.

Two flags Step 3 passes that are worth reusing when a run misbehaves: `-p no:cacheprovider` (keeps pytest from writing `.pytest_cache` into the repo tree) and a timeout discipline — the pipeline kills a suite after 120s, so a hang under bare pytest is a hang the pipeline would have scored as *unscored*, not as a failure.

One caveat when reading bare-pytest output: a **skip** usually means the generation file was missing or a capability is absent, and pytest alone won't distinguish those from "not applicable." `coverage_rate` in the Step 3 JSON is what separates them.

#### Output — `repos/<repo>/results.json`

One entry per implementation id.

NL (run0 only — counts describe that one generation):
```json
{
  "nl/claude": {
    "total": 12,
    "passed": 10,
    "failed": 1,
    "skipped": 1,
    "failed_tests": ["test_...[nl/claude]"],
    "test_case_pass_rate": 0.8333,
    "coverage_rate": 0.9167,
    "pass_at_1": 0
  }
}
```

UML (10 generations per cell — every count is **pooled over the runs**, so `passed / total` is exactly `test_case_pass_rate`, and `failed_tests` records every failure from every run, run-labelled):
```json
{
  "uml/gemini": {
    "total": 100,
    "passed": 72,
    "failed": 28,
    "skipped": 0,
    "test_case_pass_rate": 0.72,
    "coverage_rate": 1.0,
    "pass_at_1": 0.0,
    "n_runs_averaged": 10,
    "failed_tests": [
      "run0: test_agent_specializes_base[uml/gemini]",
      "run1: test_task_status_refs_task_status[uml/gemini]"
    ],
    "per_run": [
      { "run": 0, "scored": true, "total": 10, "passed": 0, "failed": 10,
        "skipped": 0, "test_case_pass_rate": 0.0, "pass_at_1": 0,
        "failed_tests": ["test_agent_specializes_base[uml/gemini]"] },
      { "run": 3, "scored": false }
    ]
  }
}
```

`per_run` is the per-generation breakdown (`scored: false` = that generation was missing or its suite timed out; it is excluded from every pooled total rather than counted as a failure). `step5_build_db.py` ignores `per_run`, so `test_results` stays at one row per (repo, variant).

- `test_case_pass_rate` = `passed / total` — **skips count against you** (an unimplemented capability is not a pass). This is partial credit *within* a cell, not pass@1.
- `coverage_rate` = `(passed + failed) / total` — the fraction actually exercised (not skipped).
- `pass_at_1` (NL) = `1` only if **every** test passed — zero failures *and* zero skips. This is Chen et al. (2021) pass@1: with one scored generation per cell it is a binary "fully correct or not," and averaging it across the 12 repos gives the reported rate. On the UML track, where each cell has 10 generations, `pass_at_1` is the *fraction* of those 10 that were fully correct (pass@1 with n=10), hence a float.

---

### Step 4 — Internal Quality (SonarQube)

Scans **every generation** — all 10 runs per cell, 960 scans total — creating one SonarQube project per run (keyed `{repo}:{condition}:{model}:run{N}`), waiting for analysis, then fetching metrics via the REST API into `sonar_results.json` per repo.

```bash
python step4_sonarqube.py
```

It takes **no arguments**: it always scans every run of every cell of every repo under `repos/`, and prints a completeness check against `EXPECTED_RUNS = 10` at the end.

**Prerequisites:**
- `pip install -r requirements.txt` (the script uses `requests`)
- SonarQube Community server running in Docker on `localhost:9000` (container name: `sonarqube`)
- In `.env`: `SONAR_TOKEN=...` (a SonarQube user token), optionally `SONAR_URL` to override `http://localhost:9000`
- No local Java or sonar-scanner CLI — it uses the Java and scanner JAR bundled inside the container

**Two delivery shapes, one code path.** A run is scanned either as the single file `<model>.run<N>.py` or, when a model emitted a whole project, as the directory `<model>.run<N>/`. Directory scans apply `DEFAULT_DIR_EXCLUSIONS` — `**/migrations/**`, `**/templates/**`, `**/*.html`, `**/*.js`, `**/*.css`, `**/manage.py`, `**/__pycache__/**`, and similar — so only the model's own Python is measured. These exclusions are deliberately **not** configurable per cell: an A/B over every directory-delivered run confirmed per-cell overrides changed no metric, so the earlier `special_cases/` override mechanism was removed.

Output — `repos/<repo>/sonar_results.json`, one entry per `condition/model/run`:
```json
{
  "nl/claude/run0": {
    "project_key": "kapitoshk4__library-service-api:nl:claude:run0",
    "bugs": 0,
    "vulnerabilities": 1,
    "code_smells": 39,
    "ncloc": 1463,
    "lines": 1773,
    "complexity": 254,
    "cognitive_complexity": 237,
    "duplicated_lines_density": 0,
    "comment_lines_density": 5.2,
    "error": null
  }
}
```

**What each metric means:**

| Field | Meaning | How to read it |
|---|---|---|
| `bugs` | Code that is demonstrably wrong and will likely misbehave at runtime (reliability issues). | Lower is better; `0` = none found. |
| `vulnerabilities` | Security-sensitive code that could be exploited (hard-coded credentials, unsafe input handling). | Lower is better; `0` = none found. |
| `code_smells` | Maintainability issues — code that works but is confusing, duplicated, overly complex, or unconventional. | Lower is better; the most common finding by far. Read relative to `ncloc`. |
| `ncloc` | Non-comment lines of code. | Size measure; use it to normalize the counts (e.g. smells per 1k lines). |
| `lines` | Total physical lines including blanks and comments. | Always ≥ `ncloc`. |
| `complexity` | Cyclomatic complexity — count of independent paths through the code. | Lower is better; scales with size, so normalize before comparing cells. |
| `cognitive_complexity` | How hard the code is for a *human* to follow; accumulates for nesting and control-flow breaks. | Lower is better. This is the metric `Reports/analysis.ipynb` uses to pick which run gets human-rated. |
| `duplicated_lines_density` | Percentage of lines duplicated elsewhere in the analyzed code. | Lower is better; `0` = none. |
| `comment_lines_density` | `comment_lines / (ncloc + comment_lines)`, as a percentage. | Interpretive, not "higher is better" — very low can mean under-documented, very high can mean noise. |
| `project_key` | The SonarQube project id: `{repo}:{condition}:{model}:run{N}`. | Bookkeeping — links the row back to its SonarQube project. |
| `error` | `null` on success, else a string describing the failure. | Any non-`null` value means that run's metrics are missing or unreliable. |

The A–E letter ratings (`sqale_rating`, `reliability_rating`, `security_rating`) are **no longer collected** — they are coarse thresholds over the raw counts already in the table, and the analysis works from the counts directly.

**Reading a row (example — `nl/claude/run0` in `library-service-api`):** no bugs, but one vulnerability worth inspecting; 39 smells is low relative to `ncloc: 1463`; `cognitive_complexity: 237` says the code is large and hard to follow. Functionally sound for its size, but dense and carrying one security flaw.

---

### Step 5 — Consolidate Results into SQLite

Walks every repo under `repos/` and loads its `results.json` (Step 3), `sonar_results.json` (Step 4), each generation's `<model>.run<N>.metadata.json` (Step 2), a derived `repos` row, and `Human Evaluation Reports/human_evaluation.csv` into `results.db`. DDL lives in `schema/<table>.sql`, one `CREATE TABLE` per file.

```bash
python step5_build_db.py
```

No arguments: it drops and recreates its four tables for every repo, so it is safe to re-run anytime. Metadata is read per generation rather than from a repo-level summary, so a repo where you generated only one condition or one model still contributes exactly the rows that exist on disk.

Missing files or fields degrade to `NULL` rather than failing. A *variant* is the `<condition>/<model>` key (`nl/gpt`) in `test_results`, and `<condition>/<model>/run<N>` (`nl/gpt/run3`) in `sonar_results`.

**Tables step5 rebuilds:**

| Table | Grain | Rows | Source |
|---|---|---|---|
| `generation_runs` | `(repo, condition, model, run)` | 960 | per-generation `metadata.json` — `model_name`, `output_tokens`, `latency_s`, `generated_at`, `code_chars = len(code)` |
| `test_results` | `(repo, variant)` | 96 | `results.json` (`per_run` ignored) |
| `sonar_results` | `(repo, variant)` where variant includes `run` | 960 | `sonar_results.json` |
| `human_evaluation` | `(repo, condition, model, metric)` | 288 | `human_evaluation.csv` — `score` is `REAL`. `readability` and `maintainability` are 1–5 (higher = better); `human_developer_proximity_rank` is 1–4 within each `(repo, condition)` block (**lower = more human-like**), so never average it with the other two |

**Tables step5 leaves alone.** These are populated out-of-band and are deliberately absent from `ALL_TABLES`, so re-running step5 does not rebuild them empty:

| Table | Rows | Written by | Notes |
|---|---|---|---|
| `repos` | 12 | one-off, from the `<owner>__<repo>` folder names | `owner`, `name`, `url`. The only surviving record of where each ground-truth clone came from. |
| `variance_pilot` | 512 | `Reports/variance_pilot/*.py` | Per-generation conformance scores; only reproducible by re-running the suites. |
| `human_eval_selection` | 24 | `Reports/analysis.ipynb` → `human_eval_selection.csv` | **Only the substituted cells.** A cell is rated on run0 unless run0's cognitive complexity falls more than one IQR from its cell median, in which case the median-closest run is rated. Absence therefore means *run0 was used* — join with `LEFT JOIN` and `COALESCE(chosen_run, 0)`, never an inner join. |

There is no `evaluation` view; join the tables directly.

Example query:
```sql
SELECT t.repo, t.condition, t.model, t.test_case_pass_rate,
       AVG(s.code_smells) AS smells, AVG(s.cognitive_complexity) AS cog
FROM test_results t
LEFT JOIN sonar_results s
  ON s.repo = t.repo AND s.condition = t.condition AND s.model = t.model
WHERE t.repo = 'kapitoshk4__library-service-api'
GROUP BY t.repo, t.condition, t.model
ORDER BY t.condition, t.model;
```

Note the `AVG` — `sonar_results` has 10 rows per cell against `test_results`' one, so an unaggregated join fans out.

---

## Adding a New Repo

1. **Search**: `python step0_search_repos.py` — find and review candidates
2. **Download**: `python step1_repo_pipeline.py --repo <owner/repo>`
3. **Write inputs** (manually):
   - `repos/<owner>__<repo>/nl/input/description.txt`
   - `repos/<owner>__<repo>/uml/input/classes.puml`
4. **Generate code**: `python step2_code_generation.py --repo <owner>__<repo> --runs 10`
5. **Author the conformance suites** (one per track under `nl/tests/` and `uml/tests/`): derive a `CONTRACT.md` from the spec + ground-truth source (behavioral for NL, structural for UML), then write `loader.py`, the adapter layer, and `test_conformance.py` — see *Conformance Suite Architecture* below. Iterate with bare pytest (Step 3, "Running a suite directly") before scoring.
6. **Correctness**: `python step3_functional_correctness.py` (NL) and `python step3_structural_fidelity.py` (UML) — both run all repos
7. **Internal quality**: `python step4_sonarqube.py` (all repos, all runs)
8. **Consolidate**: `python step5_build_db.py`
9. **Human rating**: add the markdown forms under `Human Evaluation Reports/<owner>__<repo>/`, transcribe into `human_evaluation.csv`, re-run step5

---

## Conformance Suite Architecture

Each track carries **one** conformance suite (not one file per model). A single shared test body runs against every generation via an adapter layer, so all implementations are held to the same contract regardless of how differently they are structured.

| File | Role |
|---|---|
| `CONTRACT.md` | The pinned contract. Each item (`Nn` for NL, `Un` for UML) is grounded in the ground-truth source via a *spec-feature → origin-evidence* table, so the tests are traceable, not arbitrary. |
| `loader.py` | Imports each generation under a unique module name (`importlib.util.spec_from_file_location` — the files share a basename pattern and would otherwise collide). Missing heavy third-party packages resolve to permissive stubs from `adapter_harness/` so a module execs far enough to expose its surface. |
| `adapter.py` (NL) / `structure.py` (UML) | Exposes **one stable interface** over each loaded generation, absorbing naming and shape differences (different class or method names, constructor signatures, sync vs async) and raising `Unsupported` when a surface is genuinely absent → the test **skips (N/A)** rather than fails. |
| `test_conformance.py` | The shared, `pytest`-parametrized test body. One `impl` fixture yields each implementation in turn; each test pins one contract item and names it in a comment. |

The two tracks differ in **what** they assert:

- **NL track — behavioral.** The contract is derived by comparing `nl/input/description.txt` with the origin code, pinning **observable capability and effect** (e.g. "a created task can be marked complete"). The adapter *exercises* behavior, so `loader.py` keeps the libraries the behaviors actually need **real** and stubs only genuinely-missing optional dependencies. Where a generation buries its logic in a widget closure rather than a method, `adapter_harness/faketk.py` stands in for tkinter and captures the callback.

- **UML track — structural.** The contract is derived from `uml/input/classes.puml`, pinning the three things a class diagram draws: **inheritance links** (`--|>`), **association links** (`A --> B : attr`), and **methods under a class**. Assertions are purely **reflective** (`issubclass`, `__annotations__`, method names) — behavior is never run.

Both are parametrized over the **4 generations only**; neither has a reference row.

**N/A vs failure** is the key distinction (see Step 3): a capability or structure a generation never defines is a *skip*, while one that is present but wrong is a *failure*. This keeps "the model didn't attempt X" separate from "the model got X wrong."

**Per-track suites are not interchangeable.** The NL and UML suites assert different things at different altitudes and are not a shared yardstick — a cross-track comparison of raw pass rates is not meaningful. The comparable signals across tracks are pass@1 within a track, the SonarQube metrics, and the human ratings.

---

## Utility Scripts

### `utils/check_size_thresholds.py` — Method & Class Size Check

Checks generated code under a repo directory against method size (≤30 lines) and class size (≤75 lines) thresholds.

```bash
python3 utils/check_size_thresholds.py repos/<owner>__<repo>
python3 utils/check_size_thresholds.py repos/<owner>__<repo> --verbose
python3 utils/check_size_thresholds.py repos/            # all repos
python3 utils/check_size_thresholds.py repos/<owner>__<repo> --method 20 --class 50
```

| Flag | Default | Description |
|---|---|---|
| `repo_dir` | `.` | Root directory to search |
| `--method N` | 30 | Max allowed lines per method |
| `--class N` | 75 | Max allowed lines per class |
| `--verbose` | off | Print each failing class/method name and line count |

Exits `1` if any file has violations, `0` if all pass.

---

### `utils/count_uml_classes.py` — UML Class Count

Counts PlantUML type declarations (`class`, `abstract class`, `interface`, `enum`, `protocol`) in each repo's `uml/input/classes.puml`.

```bash
python3 utils/count_uml_classes.py
python3 utils/count_uml_classes.py --repo hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact
python3 utils/count_uml_classes.py --by-kind
python3 utils/count_uml_classes.py --csv classes.csv
```

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `repos/` |
| `--by-kind` | off | Break counts down by keyword |
| `--csv PATH` | none | Also write results to a CSV file |

---

## Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys + SONAR_TOKEN
```

`requirements.txt` holds the pinned direct dependencies, grouped by which step needs them (pipeline / test harness / analysis). `requirements.lock.txt` is the full transitive freeze — use it to reproduce the exact environment the reported results came from:

```bash
pip install -r requirements.lock.txt
```
