# POC-v1 — Thesis Evaluation Pipeline

End-to-end pipeline for comparing LLM code generation quality from natural-language (NL) and UML specifications, measured via pass@1.

---

## Repository Layout

```
POC-v1/
├── step0_search_repos.py        ← Search GitHub for candidate repos by quality
├── step1_repo_pipeline.py       ← Download repo zip & scaffold folder structure
├── step2_code_generation.py     ← Call LLMs to generate code from NL / UML inputs
├── step3_functional_correctness.py ← NL: run behavioural suite, pass@1
├── step3_structural_fidelity.py    ← UML: run structural suite, 10-run mean
├── step3_common.py                 ← shared internals for both (library, no CLI)
├── step4_sonarqube.py           ← Run SonarQube analysis & collect code quality metrics
├── step5_build_db.py            ← Consolidate all per-repo results (+ human eval) into a SQLite database
├── results.db                   ← SQLite database written by step5 (generated) — tables:
│                                    repos, generation_runs, test_results, sonar_results,
│                                    human_evaluation, plus the `evaluation` view
├── Human Evaluation Reports/     ← Manually-scored human evaluation
│   ├── <owner>__<repo>/          ← one markdown rating form per generation:
│   │   └── <repo>_<NL|UML>_<Model>.md   readability, maintainability, proximity rank
│   └── human_evaluation.csv     ← the forms' scores transcribed into one long-format
│                                    CSV (repo, condition, model, metric, score) — the
│                                    file step5 actually reads
├── special_cases/                ← Step 4 overrides for models that emit a full project
│   └── <owner>__<repo>/          ← tree instead of a single generated_code.py
│       └── <condition>/<model>/config.json
├── utils/
│   ├── check_size_thresholds.py ← Check method/class size thresholds across generated_code files
│   └── count_uml_classes.py     ← Count class declarations in each repo's UML diagram
├── Reports/                      ← (contents omitted — see folder directly)
├── repos/                ← One folder per evaluated repo (original source clone removed
│   └── <owner>__<repo>/            after scoring; see `repos` table in results.db for name/URL)
│       ├── nl/
│       │   ├── input/
│       │   │   └── description.txt      ← NL specification (written manually)
│       │   ├── outputcode/
│       │   │   └── <model>/
│       │   │       ├── generated_code.py
│       │   │       └── metadata.json      ← model, tokens, latency, timestamp, code
│       │   └── tests/                   ← NL behavioral conformance suite
│       │       ├── CONTRACT.md          ← behaviors pinned (Nn) + origin grounding
│       │       ├── loader.py            ← loads the 4 generations (real libs, stubs missing)
│       │       ├── adapter.py           ← one interface over each generation (by behavior)
│       │       ├── test_conformance.py  ← shared test body, parametrized over the 4 models
│       │       └── RESULTS.md           ← per-model pass/fail/skip write-up
│       └── uml/
│           ├── input/
│           │   └── classes.puml         ← PlantUML class diagram (written manually)
│           ├── outputcode/
│           │   └── <model>/
│           │       ├── generated_code.py
│           │       └── metadata.json      ← model, tokens, latency, timestamp, code
│           └── tests/                   ← UML structural conformance suite
│               ├── CONTRACT.md          ← facts pinned (Un) + origin grounding
│               ├── loader.py            ← loads the 4 generations (stubs heavy deps)
│               ├── adapter.py           ← one interface over each generation (by reflection)
│               ├── test_conformance.py  ← shared test body, parametrized over the 4 models
│               └── RESULTS.md           ← per-model pass/fail/skip write-up
├── .env                         ← API keys (never commit)
├── requirements.txt
└── README.md
```

`results.json` and `sonar_results.json` (Steps 3 & 4 output) are no longer kept under each `repos/<repo>/` — once loaded into `results.db` via Step 5 they were deleted to save space. See the warning in `step5_build_db.py` before deleting them again on a future run: those two tables can't be rebuilt from scratch once the source JSON is gone.

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

Options:

| Flag | Default | Description |
|---|---|---|
| `--max-results N` | 50 | Number of repos to return per query |
| `--min-stars N` | 1 | Minimum GitHub stars |
| `--max-stars N` | 1000 | Maximum GitHub stars |

After reviewing the ranked list, pick a repo and download it with Step 1.

Required in `.env`:
```
GITHUB_TOKEN=...  (optional but recommended for higher API rate limits)
```

---

### Step 1 — Download Repo & Scaffold

Downloads a GitHub repo as a zip and extracts it into `repos/<owner>__<repo>/<repo>-main/`. Also creates the full folder scaffold (`nl/input/`, `nl/outputcode/`, `nl/tests/`, `uml/input/`, `uml/outputcode/`, `uml/tests/`).

```bash
python step1_repo_pipeline.py <github-url-or-owner/repo>
```

Examples:
```bash
python step1_repo_pipeline.py --repo https://github.com/ecopque/new_banking_system
python step1_repo_pipeline.py --repo ecopque/new_banking_system
```

After Step 1, manually create the inputs:
- `repos/<owner>__<repo>/nl/input/description.txt` — natural language description of the system
- `repos/<owner>__<repo>/uml/input/classes.puml` — PlantUML class diagram

#### Generating `classes.puml` with pyreverse

To automatically extract the UML class diagram from the downloaded repo's source code, use `pyreverse` (part of pylint):

```bash
# Install pyreverse (if not already installed)
pip install pylint

# Generate PlantUML diagram from source code
cd repos/<owner>__<repo>/<repo>-main/
pyreverse -o puml -p ProjectName path/to/models.py path/to/other_modules/
```

This creates `.puml` files in the current directory. Move the most relevant one to the UML input folder:

```bash
mv classes.puml ../uml/input/classes.puml
```

You can also open `.puml` files in VS Code with the PlantUML extension to preview the diagram.

---

### Step 2 — LLM Code Generation

Reads the NL description and/or UML diagram for each repo and calls all configured LLMs. Saves generated code and metadata to `outputcode/<model>/` under each condition.

```bash
# All repos, both conditions, all models
python step2_code_generation.py

# Single repo
python step2_code_generation.py --repo ecopque__new_banking_system

# Single condition
python step2_code_generation.py --repo ecopque__new_banking_system --condition nl

# Specific models only
python step2_code_generation.py --repo ecopque__new_banking_system --models claude gpt
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `repos/` |
| `--condition` | `both` | `nl`, `uml`, or `both` |
| `--models` | all | One or more of: `claude gpt gemini deepseek` |

Output per model:
- `<condition>/outputcode/<model>/generated_code.py` — generated implementation
- `<condition>/outputcode/<model>/metadata.json` — the durable per-generation record: `model` (display name), `output_tokens`, `latency_s`, `generated_at`, and the generated `code`. This is what Step 5 reads, so regenerating a single condition/model never clobbers the others' records.

Required in `.env`:
```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
```

---

### Step 3 — Correctness Evaluation (pass@1)

Runs the per-track **conformance suite** under each repo's `nl/tests/` and `uml/tests/` directories with `pytest` (one subprocess per track), parses the JUnit XML, groups test cases by the implementation each one exercises, and writes results to `repos/<repo>/results.json`.

Each track ships **one** shared `test_conformance.py` that is parametrized over that track's **4 generated implementations only** (parametrize ids like `nl/claude`, `uml/gpt`) — **there is no `reference` row**. Both the NL and UML tracks evaluate the four generations against a contract authored from the ground-truth source; the original repo's source is not run as a row. (A legacy single-suite fallback at `<repo>/tests/` may still contain a `reference` row, but the per-track suites used by every current repo do not.)

**Prerequisite:** install the Python dependencies first — the conformance suites import the same runtime libraries the generated code uses (`pytest`, `Django`, `fastapi`, `SQLAlchemy`, …):

```bash
pip install -r requirements.txt
```

```bash
# All repos
python step3_functional_correctness.py    # NL
python step3_structural_fidelity.py       # UML

# Single repo
python step3_functional_correctness.py --repo ecopque__new_banking_system

# Single condition
python step3_structural_fidelity.py --repo ecopque__new_banking_system

# Specific models
python step3_functional_correctness.py --repo ecopque__new_banking_system --models claude gpt
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `repos/` |
| `--condition` | `both` | `nl`, `uml`, or `both` |
| `--models` | all discovered | One or more model keys |

A test outcome is one of three, and **skips are reported separately from failures**: a *skip* means the implementation lacks that capability/structure entirely (the adapter raised `Unsupported`, reported as **N/A**), whereas a *failure* means the capability exists but behaves or is shaped wrongly.

Output — `repos/<repo>/results.json` (one entry per implementation id):
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
  },
  ...
}
```

- `test_case_pass_rate` = `passed / total` — **skips count against you** (an unimplemented capability is not a pass). This is partial credit *within one generation* (fraction of its test cases that passed), not pass@1 — see below.
- `coverage_rate` = `(passed + failed) / total` — the fraction that was actually exercised (not skipped).
- `pass_at_1` = `1` only if **every** test passed — i.e. zero failures *and* zero skips (skips count against, same as failures). This is the actual Chen et al. (2021) pass@1: with one generation per (condition, model, repo), it's a binary "fully correct or not" outcome; averaging it across the 12 repos gives the reported pass@1 rate for a model/condition.

---

### Step 4 — Code Quality Evaluation (SonarQube)

Runs SonarQube static analysis on each `generated_code.py` file. Creates one SonarQube project per file (keyed as `{repo}:{condition}:{model}`), waits for analysis to complete, then fetches metrics via the SonarQube REST API and writes them to `sonar_results.json` per repo.

**Prerequisites:**
- Python dependencies installed (`pip install -r requirements.txt`) — the script uses `requests` to talk to the SonarQube REST API
- SonarQube Community server running in Docker on `localhost:9000` (container name: `sonarqube`)
- A SonarQube user token stored in `step4_sonarqube.py` as `SONAR_TOKEN`
- No local Java or sonar-scanner CLI needed — uses the Java and scanner JAR bundled inside the container

```bash
# All repos
python step4_sonarqube.py

# Single repo
python step4_sonarqube.py --repo kapitoshk4__library-service-api

# Single condition
python step4_sonarqube.py --repo kapitoshk4__library-service-api --condition uml

# Specific models only
python step4_sonarqube.py --repo kapitoshk4__library-service-api --models claude gpt
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `repos/` |
| `--condition` | `both` | `nl`, `uml`, or `both` |
| `--models` | all | One or more of: `claude gpt gemini deepseek` |

Output — `repos/<repo>/sonar_results.json`:
```json
{
  "nl/claude": {
    "project_key": "kapitoshk4__library-service-api:nl:claude",
    "bugs": 0,
    "vulnerabilities": 0,
    "code_smells": 7,
    "sqale_rating": "A",
    "reliability_rating": "A",
    "security_rating": "A",
    "ncloc": 1591,
    "lines": 1658,
    "cognitive_complexity": 0,
    "duplicated_lines_density": 0,
    "comment_lines_density": 1.4,
    "error": null
  },
  ...
}
```

**What each metric means:**

| Field | Meaning | How to read it |
|---|---|---|
| `bugs` | Count of code that is demonstrably wrong and will likely produce incorrect behavior at runtime (reliability issues). | Lower is better; `0` = no reliability defects found. |
| `vulnerabilities` | Count of security-sensitive code that could be exploited (e.g. hard-coded credentials, unsafe input handling). | Lower is better; `0` = no security defects found. |
| `code_smells` | Count of maintainability issues — code that works but is confusing, duplicated, overly complex, or violates conventions. | Lower is better; these are the most common finding and drive the `sqale_rating`. |
| `sqale_rating` | **Maintainability** rating (A–E), derived from estimated remediation effort (technical debt) relative to code size. | A = best (little/no debt), E = worst. Driven by `code_smells`. |
| `reliability_rating` | **Reliability** rating (A–E), derived from the number and severity of `bugs`. | A = no bugs; each worse letter reflects at least one bug of increasing severity. |
| `security_rating` | **Security** rating (A–E), derived from the number and severity of `vulnerabilities`. | A = no vulnerabilities; e.g. `C` typically means ≥1 major vulnerability. |
| `ncloc` | Non-comment lines of code (the actual executable code size). | A raw size measure; useful to normalize other counts (e.g. smells per 1k lines). |
| `lines` | Total physical lines in the file, including blanks and comments. | Always ≥ `ncloc`. |
| `cognitive_complexity` | How hard the code is for a human to understand — accumulates for nested loops, branches, and control-flow breaks. | Lower is better; high values flag code that is difficult to follow and maintain. |
| `duplicated_lines_density` | Percentage of lines that are duplicated elsewhere in the analyzed code. | Lower is better; `0` = no duplication. |
| `comment_lines_density` | Percentage of lines that are comments (`comment_lines / (ncloc + comment_lines)`). | Interpretive, not "higher is better" — very low can mean under-documented, very high can mean noise. |
| `project_key` | The SonarQube project identifier for this file: `{repo}:{condition}:{model}`. | Bookkeeping — links the row back to its SonarQube project. |
| `error` | `null` on success, or a string describing the failure (e.g. file not found, scanner crash). | Any non-`null` value means the metrics for that entry are missing/unreliable. |

**How the three ratings work (A–E, A = best):** each of `sqale_rating` (maintainability), `reliability_rating`, and `security_rating` is a letter grade SonarQube computes from the corresponding issue counts. `A` means clean; worse letters indicate more/severe issues in that dimension. In practice a generation can score `A` on maintainability (`sqale_rating`) while dropping to `C` on `security_rating` because it introduced one or more vulnerabilities — the ratings are independent axes, so read all three together with the raw counts.

**Interpreting a row (example — `nl/claude` in `library-service-api`):** `bugs: 0` and `reliability_rating: A` (no runtime defects), but `vulnerabilities: 1` pushing `security_rating` to `C` (one exploitable issue), `code_smells: 39` yet still `sqale_rating: A` (39 smells is low relative to its `ncloc: 1463`), and a high `cognitive_complexity: 237` (the code is large and hard to follow). Read together: functionally sound and maintainable for its size, but carries a security flaw worth inspecting.

#### Special cases — scanning a directory instead of a single file

The default path scans one `generated_code.py` per `{condition}/{model}`. Some models, however, ignore the "single file" instruction and emit a **full multi-file project tree** (e.g. DeepSeek expanding an output into a complete multi-app Django project). For those, there is no `generated_code.py` to scan, so the step reads an override from:

```
special_cases/<repo>/<condition>/<model>/config.json
```

When such a config exists, the step scans the specified directory tree (honoring `exclusions`) instead of a single file. The config fields are:

| Field | Meaning |
|---|---|
| `sources` | Path (relative to the repo dir) of the project tree to scan instead of `generated_code.py`. |
| `exclusions` | List of `sonar.exclusions` glob patterns to drop from the scan (e.g. `**/migrations/**`, `**/*.html`, `db.sqlite3`). |
| `reason` | Human note explaining why this generation needs a directory scan (not used by the scanner). |

Example — `special_cases/kapitoshk4__library-service-api/nl/deepseek/config.json`:
```json
{
  "reason": "deepseek expanded the single-file output into a full multi-app Django project tree, so there is no generated_code.py. Scan the whole tree instead.",
  "sources": "nl/outputcode/deepseek",
  "exclusions": [
    "**/__pycache__/**",
    "**/migrations/**",
    "db.sqlite3",
    "generated_code(original).py",
    "metadata.json",
    "manage.py",
    "templates/**",
    "**/*.html"
  ]
}
```

In the run log these appear as `(special-case dir scan)`. If a config points at a `sources` directory that does not exist, that entry is skipped with `error: "special_case_sources_not_found"`. Currently configured special cases:

| Repo | Variant |
|---|---|
| `hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact` | `nl/deepseek` |
| `kapitoshk4__library-service-api` | `nl/deepseek`, `nl/gpt` |

---

### Step 5 — Consolidate Results into SQLite

Walks every repo under `repos/` and loads its `results.json` (Step 3), `sonar_results.json` (Step 4), each model's `metadata.json` (Step 2, at `<condition>/outputcode/<model>/metadata.json`), a derived `repos` row (owner/name/GitHub URL, from the `<owner>__<repo>` folder name — no clone needed on disk), and the shared `Human Evaluation Reports/human_evaluation.csv` into a single SQLite database. The schema is dropped and recreated on each run, so it is safe to re-run anytime.

Generation metadata is read per model from `metadata.json` rather than a repo-level summary file, so a repo where you only generated one condition or one model still contributes exactly the rows that exist on disk — nothing is lost or overwritten.

```bash
python step5_build_db.py
```

It takes no arguments: it always rebuilds every table for every repo under `repos/`, writing to `results.db`.

A *variant* is the `<condition>/<model>` key (e.g. `nl/gpt`). (Only if a repo uses the legacy single-suite fallback will `results.json` also carry a `reference` variant, with `model` left `NULL`; the current per-track suites produce no reference row.) Missing files or fields degrade to `NULL` rather than failing.

**Tables:**

| Table | Grain | Source |
|---|---|---|
| `generation_runs` | `(repo, condition, model)` | per-model `metadata.json` (`condition`/`model` from the path; `model_name`, `output_tokens`, `latency_s`, `generated_at`, and `code_chars = len(code)` from the file) |
| `test_results` | `(repo, variant)` | `results.json` |
| `sonar_results` | `(repo, variant)` | `sonar_results.json` |
| `human_evaluation` | `(repo, condition, model, metric)` | `Human Evaluation Reports/human_evaluation.csv` — `score` is a `REAL`. `readability` and `maintainability` are 1–5 (higher = better); `human_developer_proximity_rank` is 1–4 within each `(repo, condition)` block (**lower = more human-like**), so never average it with the other two |

**Tables in `results.db` that step5 does *not* build.** These are populated out-of-band and are deliberately absent from step5's table list, so running `python step5_build_db.py` leaves them untouched rather than rebuilding them empty:

| Table | Written by | Notes |
|---|---|---|
| `repos` | one-off, from the `<owner>__<repo>` folder names | `owner`, `name`, and `url` (`https://github.com/<owner>/<name>`). Written once; step5 no longer rebuilds it. |
| `variance_pilot` | `Reports/variance_pilot/` | Per-generation conformance scores across the 10 runs; only reproducible by re-running the suites. |
| `human_eval_selection` | `Reports/analysis.ipynb` → `Reports/human_eval_selection.csv` | **Only the 24 substituted cells.** A cell is rated on run 0 unless run 0's cognitive complexity falls more than one IQR from its cell median, in which case the median-closest run is rated instead. Absence from this table therefore means *run 0 was used* — join with `LEFT JOIN` and `COALESCE(chosen_run, 0)`, never an inner join. |

Example query:
```sql
SELECT t.repo, t.condition, t.model, t.test_case_pass_rate, s.code_smells, s.cognitive_complexity
FROM test_results t
LEFT JOIN sonar_results s
  ON s.repo = t.repo AND s.condition = t.condition AND s.model = t.model
WHERE t.repo = 'kapitoshk4__library-service-api'
ORDER BY t.condition, t.model;
```

---

## Adding a New Repo

1. **Search**: `python step0_search_repos.py` — find and review candidate repos
2. **Download**: `python step1_repo_pipeline.py --repo <owner/repo>`
3. **Write inputs** (manually):
   - `repos/<owner>__<repo>/nl/input/description.txt`
   - `repos/<owner>__<repo>/uml/input/classes.puml`
4. **Generate code**: `python step2_code_generation.py --repo <owner>__<repo>`
5. **Author the conformance suites** (one per track under `nl/tests/` and `uml/tests/`): derive a `CONTRACT.md` from the spec + ground-truth source (behavioral for NL, structural for UML), then write `loader.py`, `adapter.py`, and `test_conformance.py` (see *Conformance Suite Architecture* below). Record per-model outcomes in `RESULTS.md`.
6. **Correctness evaluation**: `python step3_functional_correctness.py --repo <owner>__<repo>` (NL)
   and `python step3_structural_fidelity.py --repo <owner>__<repo>` (UML)
7. **Code quality evaluation**: `python step4_sonarqube.py --repo <owner>__<repo>`
8. **Consolidate results**: `python step5_build_db.py` (rebuilds `results.db` across all repos)

---

## Conformance Suite Architecture

Each track carries **one** conformance suite (not one file per model). A single shared test body runs against every generation via an adapter, so all implementations are held to the same contract regardless of how differently they are structured. Every suite has five files:

| File | Role |
|---|---|
| `CONTRACT.md` | The pinned contract. Each item (`Nn` for NL, `Un` for UML) is grounded in the ground-truth source via a *spec-feature → origin-evidence* table, so the tests are traceable, not arbitrary. |
| `loader.py` | Imports each `outputcode/<model>/generated_code.py` under a unique module name. Missing heavy third-party packages are resolved to permissive stubs so a module execs far enough to expose its surface. |
| `adapter.py` | Exposes **one stable interface** over each loaded generation. It absorbs naming/shape differences (different class or method names, constructor signatures, sync vs async) and raises `Unsupported` when a surface is genuinely absent → the test **skips (N/A)** rather than fails. |
| `test_conformance.py` | The shared, `pytest`-parametrized test body. One `impl` fixture yields each implementation in turn; each test pins one contract item and names it in a comment. |
| `RESULTS.md` | Human-readable per-model pass/fail/skip write-up and interpretation. |

The two tracks differ in **what** they assert:

- **NL track — behavioral.** The contract is derived by comparing `nl/input/description.txt` with the origin code, pinning **observable capability and effect** (e.g. "a created task can be marked complete"). The adapter *exercises* behavior. `loader.py` keeps the system libraries the behaviors actually need **real** and stubs only genuinely-missing optional dependencies. Parametrized over the **4 generations only** (no reference row).

- **UML track — structural.** The contract is derived from `uml/input/classes.puml`, pinning the three things a class diagram draws: **inheritance links** (`--|>`), **association links** (`A --> B : attr`), and **methods under a class**. The adapter asserts purely by **reflection** (`issubclass`, `__annotations__`, method names) — it never runs behavior. Parametrized over the **4 generations only** (no reference row), same as the NL track.

**N/A vs failure** is the key distinction (see Step 3): a capability/structure a generation never defines is a *skip*, while one that is present but wrong is a *failure*. This keeps "the model didn't attempt X" separate from "the model got X wrong."

---

## Utility Scripts

### `utils/check_size_thresholds.py` — Method & Class Size Check

Checks all `generated_code.py` files under a repo directory against method size (≤30 lines) and class size (≤75 lines) thresholds.

```bash
# All generated_code.py files under a repo
python3 utils/check_size_thresholds.py repos/<owner>__<repo>

# With per-violation detail
python3 utils/check_size_thresholds.py repos/<owner>__<repo> --verbose

# All repos at once
python3 utils/check_size_thresholds.py repos/

# Custom thresholds
python3 utils/check_size_thresholds.py repos/<owner>__<repo> --method 20 --class 50
```

Options:

| Flag | Default | Description |
|---|---|---|
| `repo_dir` | `.` | Root directory to search for `generated_code.py` files |
| `--method N` | 30 | Max allowed lines per method |
| `--class N` | 75 | Max allowed lines per class |
| `--verbose` | off | Print each failing class/method name and line count |

Exits with code `1` if any file has violations, `0` if all pass.

---

### `utils/count_uml_classes.py` — UML Class Count

Counts PlantUML type declarations (`class`, `abstract class`, `interface`, `enum`, `protocol`) in each repo's `uml/input/classes.puml`.

```bash
# Table for all repos
python3 utils/count_uml_classes.py

# Single repo
python3 utils/count_uml_classes.py --repo hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact

# Break down by declaration keyword
python3 utils/count_uml_classes.py --by-kind

# Export to CSV
python3 utils/count_uml_classes.py --csv classes.csv
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `repos/` |
| `--by-kind` | off | Break counts down by keyword (`class`, `interface`, etc.) |
| `--csv PATH` | none | Also write results to a CSV file |

---

## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
```
