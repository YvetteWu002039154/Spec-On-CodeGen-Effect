"""
Usage:
    python step5_build_db.py        # all repos, all tables -> results.db

Reads, for each repo under repos/<repo>/:
    results.json             — pytest / pass@1 metrics per (condition, model), run0
    sonar_results.json       — SonarQube metrics per (condition, model, run)
    <cond>/outputcode/<model>.run<N>.metadata.json
                             — per-run metadata (model, run, tokens, latency, ...)

Produces a fresh SQLite database with these tables:
    generation_runs  — one row per (repo, condition, model) generation run
    test_results     — one row per (repo, variant) from results.json
    sonar_results    — one row per (repo, variant) from sonar_results.json
    human_evaluation — one row per (repo, condition, model, metric) from
                       "Human Evaluation Reports/human_evaluation.csv"
"""

import csv
import json
import os
import re
import sqlite3

REPOS_DIR = os.path.join(os.path.dirname(__file__), "repos")

HUMAN_EVAL_CSV = os.path.join(
    os.path.dirname(__file__), "Human Evaluation Reports", "human_evaluation.csv"
)

DB_PATH = os.path.join(os.path.dirname(__file__), "results.db")

CONDITIONS = ["nl", "uml"]


# ────────────────────────── Helpers ──────────────────────────

def load_json(path: str, missing_table: str = ""):
    """Return parsed JSON, or None if the file is missing/unreadable."""
    if not os.path.isfile(path):
        if missing_table:
            print(f"  [WARN] {path} missing — {missing_table} will be rebuilt "
                  "with 0 rows for this repo")
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] could not read {path}: {e}")
        return None

def split_variant(variant: str):
    """'nl/gpt' -> ('nl', 'gpt');"""
    if "/" in variant:
        condition, model = variant.split("/", 1)
        return condition, model
    return variant, None


def split_sonar_variant(variant: str):
    """'nl/gpt/run3' -> ('nl', 'gpt', 3)."""
    condition, model, run = variant.split("/")
    return condition, model, int(run.removeprefix("run"))


# ────────────────────────── Schema ──────────────────────────
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schema")

ALL_TABLES = ["generation_runs", "test_results", "sonar_results", "human_evaluation"]

_CREATE_RE = re.compile(r"^CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)", re.I | re.M)


def load_schema(table: str) -> str:
    """Return the CREATE statement for `table` from schema/<table>.sql."""
    path = os.path.join(SCHEMA_DIR, f"{table}.sql")
    try:
        with open(path) as f:
            ddl = f.read().strip()
    except FileNotFoundError:
        raise RuntimeError(f"no schema file for table {table!r}: {path}") from None
    m = _CREATE_RE.search(ddl)
    if not m:
        raise RuntimeError(f"{path}: no CREATE TABLE statement")
    if m.group(1) != table:
        raise RuntimeError(f"{path}: defines table {m.group(1)!r}, not {table!r}")
    return ddl


TABLE_SCHEMAS = {t: load_schema(t) for t in ALL_TABLES}

# ── variance_pilot — written by Reports/variance_pilot/, NOT rebuilt here ─────

def _ensure_variance_table(conn):
    """Create variance_pilot if absent."""
    conn.execute(load_schema("variance_pilot"))


def write_variance_pilot(rows, db_path: str = DB_PATH) -> int:
    """Upsert per-run conformance scores into variance_pilot; return row count."""
    cols = ["repo", "condition", "adapter", "model", "run", "test_case_pass_rate", "passed",
            "failed", "skipped", "total", "pass_at_1", "failed_tests"]
    conn = sqlite3.connect(db_path)
    try:
        _ensure_variance_table(conn)
        conn.executemany(
            f"INSERT OR REPLACE INTO variance_pilot ({','.join(cols)}) "
            f"VALUES ({','.join('?' * len(cols))})",
            [tuple(r.get(c) for c in cols) for r in rows],
        )
        conn.commit()
    finally:
        conn.close()
    return len(rows)

HUMAN_EVAL_ROWS_BY_REPO: dict = {}

# ────────────────────────── Loaders ──────────────────────────

def insert_human_evaluation(cur, repo: str) -> int:
    """Insert this repo's rows from the pre-loaded human-evaluation CSV."""
    rows = HUMAN_EVAL_ROWS_BY_REPO.get(repo, ())
    for condition, model, metric, score in rows:
        cur.execute(
            "INSERT OR REPLACE INTO human_evaluation VALUES (?,?,?,?,?)",
            (repo, condition, model, metric, score),
        )
    return len(rows)


def load_human_eval_csv() -> dict:
    """Read HUMAN_EVAL_CSV into {repo: [(condition, model, metric, score), ...]}."""
    if not os.path.isfile(HUMAN_EVAL_CSV):
        print(f"  [WARN] {HUMAN_EVAL_CSV} not found — human_evaluation will be empty")
        return {}
    index: dict = {}
    with open(HUMAN_EVAL_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            repo = (row.get("repo") or "").strip()
            if not repo:
                continue
            index.setdefault(repo, []).append((
                row["condition"].strip(),
                row["model"].strip(),
                row["metric"].strip(),
                float(row["score"]),
            ))
    return index


_META_RE = re.compile(r"^(?P<model>[A-Za-z0-9_]+)\.run(?P<run>\d+)\.metadata\.json$")
_RUNDIR_RE = re.compile(r"^(?P<model>[A-Za-z0-9_]+)\.run(?P<run>\d+)$")


def insert_generation_runs(cur, repo: str, repo_dir: str) -> int:
    """Read every run's metadata sidecar under <cond>/outputcode/.

    Two layouts per condition, both carrying condition/model/run in the path:
      * flat sidecar  <model>.run<N>.metadata.json  (single-file run)
      * run folder    <model>.run<N>/metadata.json  (multi-file project run)
    """
    def _insert(condition, model, run, meta):
        code = meta.get("code")
        code_chars = len(code) if isinstance(code, str) else None
        cur.execute(
            "INSERT OR REPLACE INTO generation_runs VALUES (?,?,?,?,?,?,?,?,?)",
            (
                repo, condition, model, run,
                meta.get("model"),
                meta.get("output_tokens"),
                meta.get("latency_s"),
                code_chars,
                meta.get("generated_at"),
            ),
        )

    n = 0
    for condition in CONDITIONS:
        outputcode_dir = os.path.join(repo_dir, condition, "outputcode")
        if not os.path.isdir(outputcode_dir):
            continue
        for entry in sorted(os.listdir(outputcode_dir)):
            path = os.path.join(outputcode_dir, entry)
            if m := _META_RE.match(entry):
                meta = load_json(path)
            elif m := _RUNDIR_RE.match(entry):
                meta = load_json(os.path.join(path, "metadata.json"))
            else:
                continue
            if meta is not None:
                _insert(condition, m["model"], int(m["run"]), meta)
                n += 1
    return n


def insert_test_results(cur, repo: str, results: dict | None):
    for variant, m in (results or {}).items():
        condition, model = split_variant(variant)
        cur.execute(
            "INSERT INTO test_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                repo,
                variant,
                condition,
                model,
                m.get("total"),
                m.get("passed"),
                m.get("failed"),
                m.get("skipped"),
                m.get("test_case_pass_rate"),
                m.get("coverage_rate"),
                m.get("pass_at_1"),
                m.get("n_runs_averaged"),
                json.dumps(m.get("failed_tests", [])),
            ),
        )


def insert_sonar_results(cur, repo: str, results: dict | None):
    for variant, m in (results or {}).items():
        condition, model, run = split_sonar_variant(variant)
        cur.execute(
            "INSERT INTO sonar_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                repo,
                variant,
                condition,
                model,
                run,
                m.get("project_key"),
                m.get("bugs"),
                m.get("vulnerabilities"),
                m.get("code_smells"),
                m.get("ncloc"),
                m.get("lines"),
                m.get("complexity"),
                m.get("cognitive_complexity"),
                m.get("duplicated_lines_density"),
                m.get("comment_lines_density"),
                m.get("error"),
            ),
        )


# ────────────────────────── Schema builder ──────────────────────────

def build_schema(cur):
    """Drop and recreate every table in ALL_TABLES.

    Tables outside ALL_TABLES (repos, variance_pilot, human_eval_selection) are written
    out-of-band and deliberately left alone — see the note above.
    """
    for table in ALL_TABLES:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        cur.executescript(TABLE_SCHEMAS[table])


# ────────────────────────── Main ──────────────────────────

def main():
    global HUMAN_EVAL_ROWS_BY_REPO
    HUMAN_EVAL_ROWS_BY_REPO = load_human_eval_csv()

    repos = sorted(d for d in os.listdir(REPOS_DIR)
                   if os.path.isdir(os.path.join(REPOS_DIR, d)))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    build_schema(cur)

    totals = {"generation_runs": 0, "test_results": 0,
              "sonar_results": 0, "human_evaluation": 0}

    for repo in repos:
        repo_dir = os.path.join(REPOS_DIR, repo)

        test = load_json(os.path.join(repo_dir, "results.json"), "test_results")
        sonar = load_json(os.path.join(repo_dir, "sonar_results.json"), "sonar_results")
        insert_test_results(cur, repo, test)
        insert_sonar_results(cur, repo, sonar)

        counts = {
            "generation_runs": insert_generation_runs(cur, repo, repo_dir),
            "test_results": len(test or {}),
            "sonar_results": len(sonar or {}),
            "human_evaluation": insert_human_evaluation(cur, repo),
        }
        for table, n in counts.items():
            totals[table] += n
        print(f"=== {repo}: " + ", ".join(f"{n} {t}" for t, n in counts.items()))

    conn.commit()
    conn.close()

    print(f"\nWrote {DB_PATH}")
    print(f"  repos processed:  {len(repos)}")
    for table, n in totals.items():
        print(f"  {table + ':':<18}{n}")


if __name__ == "__main__":
    main()
