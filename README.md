# POC-v1 — Thesis Evaluation Pipeline

End-to-end pipeline for comparing LLM code generation quality from natural-language (NL) and UML specifications, measured via pass@1.

---

## Repository Layout

```
POC-v1/
├── step1_repo_pipeline.py       ← Download repo zip & scaffold folder structure
├── step2_code_generation.py     ← Call LLMs to generate code from NL / UML inputs
├── step3_passatk.py             ← Run tests & compute pass@1 metrics
├── thesis_repos/                ← One folder per evaluated repo
│   └── <owner>__<repo>/
│       ├── <repo>-main/         ← Downloaded source repo (ground truth)
│       ├── behaviors.md         ← Test behavior specification (written manually)
│       ├── results.json         ← pass@1 results written by step3
│       ├── nl/
│       │   ├── input/
│       │   │   └── description.txt      ← NL specification (written manually)
│       │   ├── outputcode/
│       │   │   └── <model>/
│       │   │       ├── generated_code.py
│       │   │       └── generation_summary.json
│       │   └── tests/
│       │       └── test_<model>.py      ← Ground-truth tests (written manually)
│       └── uml/
│           ├── input/
│           │   └── classes.puml         ← PlantUML class diagram (written manually)
│           ├── outputcode/
│           │   └── <model>/
│           │       ├── generated_code.py
│           │       └── generation_summary.json
│           └── tests/
│               └── test_<model>.py      ← Ground-truth tests (written manually)
├── .env                         ← API keys (never commit)
├── requirements.txt
└── README.md
```

---

## Models

| Key | Model |
|---|---|
| `claude` | Claude Sonnet 4.6 |
| `gpt` | GPT-5.4 |
| `gemini` | Gemini 3.1 Pro |
| `deepseek` | DeepSeek V4-Pro |

---

## Three-Step Workflow

### Step 1 — Download Repo & Scaffold

Downloads a GitHub repo as a zip and extracts it into `thesis_repos/<owner>__<repo>/<repo>-main/`. Also creates the full folder scaffold (`nl/input/`, `nl/outputcode/`, `nl/tests/`, `uml/input/`, `uml/outputcode/`, `uml/tests/`).

```bash
python step1_repo_pipeline.py --repo <github-url-or-owner/repo>
```

Examples:
```bash
python step1_repo_pipeline.py --repo https://github.com/ecopeque/new_banking_system
python step1_repo_pipeline.py --repo ecopeque/new_banking_system
```

After Step 1, manually create the inputs:
- `thesis_repos/<owner>__<repo>/nl/input/description.txt` — natural language description of the system
- `thesis_repos/<owner>__<repo>/uml/input/classes.puml` — PlantUML class diagram

---

### Step 2 — LLM Code Generation

Reads the NL description and/or UML diagram for each repo and calls all configured LLMs. Saves generated code and metadata to `outputcode/<model>/` under each condition.

```bash
# All repos, both conditions, all models
python step2_code_generation.py

# Single repo
python step2_code_generation.py --repo ecopeque__new_banking_system

# Single condition
python step2_code_generation.py --repo ecopeque__new_banking_system --condition nl

# Specific models only
python step2_code_generation.py --repo ecopeque__new_banking_system --models claude gpt
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `thesis_repos/` |
| `--condition` | `both` | `nl`, `uml`, or `both` |
| `--models` | all | One or more of: `claude gpt gemini deepseek` |

Output per model:
- `<condition>/outputcode/<model>/generated_code.py` — generated implementation
- `<condition>/outputcode/<model>/generation_summary.json` — model, tokens, timestamp

Required in `.env`:
```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
```

---

### Step 3 — Correctness Evaluation (pass@1)

Discovers test files under each repo's `nl/tests/` and `uml/tests/` directories, runs them with `pytest` (one subprocess per file), and writes results to `thesis_repos/<repo>/results.json`.

```bash
# All repos
python step3_passatk.py

# Single repo
python step3_passatk.py --repo ecopeque__new_banking_system

# Single condition
python step3_passatk.py --repo ecopeque__new_banking_system --condition uml

# Specific models
python step3_passatk.py --repo ecopeque__new_banking_system --models claude gpt
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--repo NAME` | all repos | Folder name under `thesis_repos/` |
| `--condition` | `both` | `nl`, `uml`, or `both` |
| `--models` | all discovered | One or more model keys |

Test files must be named `test_<model>.py` and be larger than 100 bytes (stub files are skipped). Each test file must insert its model's `outputcode/<model>/` directory into `sys.path` and import from `generated_code`.

Output — `thesis_repos/<repo>/results.json`:
```json
{
  "nl/claude": {
    "total": 12,
    "passed": 12,
    "failed": 0,
    "failed_tests": [],
    "pass_at_1_rate": 1.0,
    "strict_pass_at_1": 1
  },
  ...
}
```

`pass_at_1_rate` is the fraction of tests passed. `strict_pass_at_1` is 1 only if every test passes.

---

## Adding a New Repo

1. **Download**: `python step1_repo_pipeline.py --repo <owner/repo>`
2. **Write inputs** (manually):
   - `thesis_repos/<owner>__<repo>/nl/input/description.txt`
   - `thesis_repos/<owner>__<repo>/uml/input/classes.puml`
3. **Generate code**: `python step2_code_generation.py --repo <owner>__<repo>`
4. **Write tests** (manually): one `test_<model>.py` per model per condition under `tests/`, testing the same behaviors derived from the ground-truth source
5. **Write behaviors.md** (manually): document what each test covers and expected pass/fail per model
6. **Evaluate**: `python step3_passatk.py --repo <owner>__<repo>`

---

## Test File Convention

Each test file follows this pattern:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../outputcode/<model>"))
sys.modules.pop("generated_code", None)
import generated_code as _m

# T01 — <behavior description>
def test_T01_...:
    ...
```

Both NL and UML test files test the **same 12 behaviors** derived from the ground-truth source. Tests are adapted to each model's naming conventions (class names, attribute names, constructor signatures) but verify identical behavioral requirements.

---

## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
```
