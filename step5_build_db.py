"""
Step 5 — Consolidate all per-repo results into a single SQLite database.

Usage:
    python step5_build_db.py                       # all repos, all tables -> results.db
    python step5_build_db.py --db thesis.db        # custom output path
    python step5_build_db.py --repo kapitoshk4__library-service-api
    python step5_build_db.py --tables sonar_results        # rebuild only that table
    python step5_build_db.py --tables sonar_results test_results

Rebuilding a subset with --tables drops and reloads only those tables; any
table not listed keeps its existing rows (the evaluation view is always
recreated). Without --tables, every table is rebuilt from scratch.

Reads, for each repo under thesis_repos/<repo>/:
    results.json             — pytest / pass@1 metrics per (condition, model)
    sonar_results.json       — SonarQube metrics per (condition, model)
    <cond>/outputcode/<model>/metadata.json
                             — per-generation metadata (model, tokens, latency, ...)

Generation metadata is read from each model's own metadata.json (durable,
one file per generation) rather than a repo-level generation_summary.json,
so regenerating a single condition/model never clobbers the others' records.

Produces a fresh SQLite database with these tables:
    repos            — one row per repo: owner, name, GitHub URL
    generation_runs  — one row per (repo, condition, model) generation run
    test_results     — one row per (repo, variant) from results.json
    sonar_results    — one row per (repo, variant) from sonar_results.json
    human_evaluation — one row per (repo, condition, model, metric) from
                       human_evaluation/<repo>.csv

A "variant" is the "<condition>/<model>" key (e.g. "nl/gpt"), plus the
special "reference" variant in results.json (the original repo's own tests).

The repo's GitHub URL is derived from the thesis_repos/<owner>__<name>
folder naming convention (see step1_repo_pipeline.py) rather than read from
the cloned source, so the original clone doesn't need to stay on disk.

WARNING: once a repo's data is loaded into results.db, its results.json and
sonar_results.json under thesis_repos/<repo>/ are safe to delete — but doing
so means test_results/sonar_results can no longer be rebuilt from scratch
for that repo (a full rebuild, or `--tables test_results sonar_results`,
will silently write 0 rows for it). Only delete those files after they're
confirmed loaded into results.db.

It also creates a convenience view:
    evaluation       — test_results LEFT JOIN sonar_results on (repo, condition, model)
"""

import argparse
import csv
import json
import os
import re
import sqlite3

REPOS_DIR = os.path.join(os.path.dirname(__file__), "thesis_repos")
HUMAN_EVAL_DIR = os.path.join(os.path.dirname(__file__), "human_evaluation")
DEFAULT_DB = os.path.join(os.path.dirname(__file__), "results.db")
CONDITIONS = ["nl", "uml"]

# human_evaluation/*.csv filenames don't always match the thesis_repos folder
# name exactly (inconsistent underscores, casing, one typo), so a few need an
# explicit override. Keyed by the CSV's basename (no extension).
HUMAN_EVAL_FILENAME_OVERRIDES = {
    "ecopque_new_banking_system": "ecopeque__new_banking_system",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_json(path: str):
    """Return parsed JSON, or None if the file is missing/unreadable."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] could not read {path}: {e}")
        return None


def split_variant(variant: str):
    """'nl/gpt' -> ('nl', 'gpt'); 'reference' -> ('reference', None)."""
    if "/" in variant:
        condition, model = variant.split("/", 1)
        return condition, model
    return variant, None


def split_repo_folder(repo: str):
    """'kapitoshk4__library-service-api' -> ('kapitoshk4', 'library-service-api').

    Matches the f"{owner}__{repo}" naming used by step1_repo_pipeline.py's
    scaffold(), so the GitHub URL can be reconstructed without the clone.
    """
    owner, _, name = repo.partition("__")
    return owner, name


def normalize_name(s: str) -> str:
    """Loosely-matchable key: lowercase, strip underscores/hyphens."""
    return re.sub(r"[_-]", "", s).lower()


# ── Schema ────────────────────────────────────────────────────────────────────

# One CREATE statement per table, keyed by table name so a subset can be
# rebuilt on its own (see --tables). Order here is the natural build order.
TABLE_SCHEMAS = {
    "repos": """
CREATE TABLE repos (
    repo   TEXT,    -- folder name, e.g. 'kapitoshk4__library-service-api'
    owner  TEXT,
    name   TEXT,
    url    TEXT,    -- e.g. 'https://github.com/kapitoshk4/library-service-api'
    PRIMARY KEY (repo)
);""",
    "generation_runs": """
CREATE TABLE generation_runs (
    repo          TEXT,
    condition     TEXT,
    model         TEXT,    -- short key (folder name), e.g. 'gpt'
    model_name    TEXT,    -- display name from metadata.json, e.g. 'GPT-5.2'
    output_tokens INTEGER,
    latency_s     REAL,
    code_chars    INTEGER,
    generated_at  TEXT,
    PRIMARY KEY (repo, condition, model)
);""",
    "test_results": """
CREATE TABLE test_results (
    repo            TEXT,
    variant         TEXT,
    condition       TEXT,
    model           TEXT,
    total           INTEGER,
    passed          INTEGER,
    failed          INTEGER,
    skipped         INTEGER,
    pass_at_1_rate  REAL,
    coverage_rate   REAL,
    strict_pass_at_1 INTEGER,
    failed_tests    TEXT,   -- JSON array
    PRIMARY KEY (repo, variant)
);""",
    "sonar_results": """
CREATE TABLE sonar_results (
    repo                     TEXT,
    variant                  TEXT,
    condition                TEXT,
    model                    TEXT,
    project_key              TEXT,
    bugs                     INTEGER,
    vulnerabilities          INTEGER,
    code_smells              INTEGER,
    sqale_rating             TEXT,
    reliability_rating       TEXT,
    security_rating          TEXT,
    ncloc                    INTEGER,
    lines                    INTEGER,
    cognitive_complexity     INTEGER,
    duplicated_lines_density REAL,
    comment_lines_density    REAL,
    error                    TEXT,
    PRIMARY KEY (repo, variant)
);""",
    "human_evaluation": """
CREATE TABLE human_evaluation (
    repo      TEXT,
    condition TEXT,
    model     TEXT,
    metric    TEXT,   -- e.g. 'READABILITY', 'MAINTAINABILITY', 'Date'
    value     TEXT,   -- numeric score as text for score metrics, raw string
                       -- (e.g. a date) otherwise; cast with CAST(value AS REAL)
                       -- for the numeric metrics
    PRIMARY KEY (repo, condition, model, metric)
);""",
}

ALL_TABLES = list(TABLE_SCHEMAS)

# Populated once in main() from build_human_eval_index(); read by
# insert_human_evaluation().
HUMAN_EVAL_PATH_BY_REPO: dict = {}

VIEW_SCHEMA = """
CREATE VIEW evaluation AS
SELECT
    t.repo,
    t.condition,
    t.model,
    t.total,
    t.passed,
    t.failed,
    t.skipped,
    t.pass_at_1_rate,
    t.coverage_rate,
    t.strict_pass_at_1,
    g.model_name     AS gen_model_name,
    g.output_tokens,
    g.latency_s,
    g.code_chars,
    g.generated_at,
    s.bugs,
    s.vulnerabilities,
    s.code_smells,
    s.sqale_rating,
    s.reliability_rating,
    s.security_rating,
    s.ncloc,
    s.lines,
    s.cognitive_complexity,
    s.duplicated_lines_density,
    s.comment_lines_density,
    s.error          AS sonar_error
FROM test_results t
LEFT JOIN sonar_results s
    ON t.repo = s.repo AND t.condition = s.condition AND t.model = s.model
LEFT JOIN generation_runs g
    ON t.repo = g.repo AND t.condition = g.condition AND t.model = g.model;
"""


# ── Loaders ─────────────────────────────────────────────────────────────────

def insert_repo(cur, repo: str):
    owner, name = split_repo_folder(repo)
    url = f"https://github.com/{owner}/{name}" if owner and name else None
    cur.execute("INSERT OR REPLACE INTO repos VALUES (?,?,?,?)", (repo, owner, name, url))


def insert_human_evaluation(cur, repo: str):
    """Load human_evaluation/<csv matching repo>.csv, if any.

    CSV format: one row per metric, columns "<condition>_<model>" (e.g.
    "nl_claude") holding the score.
    """
    csv_path = HUMAN_EVAL_PATH_BY_REPO.get(repo)
    if csv_path is None:
        return 0
    n = 0
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            metric = row.get("Metric")
            if not metric:
                continue
            for col, value in row.items():
                if col == "Metric" or not value:
                    continue
                condition, _, model = col.partition("_")
                cur.execute(
                    "INSERT OR REPLACE INTO human_evaluation VALUES (?,?,?,?,?)",
                    (repo, condition, model, metric, value),
                )
                n += 1
    return n


def build_human_eval_index() -> dict:
    """Map thesis_repos folder name -> matching human_evaluation CSV path.

    Matches by normalized name (see normalize_name), with explicit overrides
    for filenames that don't normalize to the same key (typos, etc).
    """
    if not os.path.isdir(HUMAN_EVAL_DIR):
        return {}
    repo_by_norm = {normalize_name(d): d for d in os.listdir(REPOS_DIR)
                    if os.path.isdir(os.path.join(REPOS_DIR, d))}
    index = {}
    for fname in os.listdir(HUMAN_EVAL_DIR):
        if not fname.endswith(".csv"):
            continue
        stem = fname[:-4]
        repo = HUMAN_EVAL_FILENAME_OVERRIDES.get(stem) or repo_by_norm.get(normalize_name(stem))
        if repo is None:
            print(f"  [WARN] human_evaluation/{fname} does not match any thesis_repos folder")
            continue
        index[repo] = os.path.join(HUMAN_EVAL_DIR, fname)
    return index


def insert_generation_runs(cur, repo: str, repo_dir: str) -> int:
    """Read each model's metadata.json under <cond>/outputcode/<model>/.

    Returns the number of generation rows inserted. The condition and model
    key come from the path; the rest of the fields come from metadata.json.
    """
    n = 0
    for condition in CONDITIONS:
        outputcode_dir = os.path.join(repo_dir, condition, "outputcode")
        if not os.path.isdir(outputcode_dir):
            continue
        for model in sorted(os.listdir(outputcode_dir)):
            meta = load_json(os.path.join(outputcode_dir, model, "metadata.json"))
            if meta is None:
                continue
            code = meta.get("code")
            code_chars = len(code) if isinstance(code, str) else None
            cur.execute(
                "INSERT OR REPLACE INTO generation_runs VALUES (?,?,?,?,?,?,?,?)",
                (
                    repo,
                    condition,
                    model,
                    meta.get("model"),
                    meta.get("output_tokens"),
                    meta.get("latency_s"),
                    code_chars,
                    meta.get("generated_at"),
                ),
            )
            n += 1
    return n


def insert_test_results(cur, repo: str, results: dict | None):
    for variant, m in (results or {}).items():
        condition, model = split_variant(variant)
        cur.execute(
            "INSERT INTO test_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                repo,
                variant,
                condition,
                model,
                m.get("total"),
                m.get("passed"),
                m.get("failed"),
                m.get("skipped"),
                m.get("pass_at_1_rate"),
                m.get("coverage_rate"),
                m.get("strict_pass_at_1"),
                json.dumps(m.get("failed_tests", [])),
            ),
        )


def insert_sonar_results(cur, repo: str, results: dict | None):
    for variant, m in (results or {}).items():
        condition, model = split_variant(variant)
        cur.execute(
            "INSERT INTO sonar_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                repo,
                variant,
                condition,
                model,
                m.get("project_key"),
                m.get("bugs"),
                m.get("vulnerabilities"),
                m.get("code_smells"),
                m.get("sqale_rating"),
                m.get("reliability_rating"),
                m.get("security_rating"),
                m.get("ncloc"),
                m.get("lines"),
                m.get("cognitive_complexity"),
                m.get("duplicated_lines_density"),
                m.get("comment_lines_density"),
                m.get("error"),
            ),
        )


# ── Schema builder ────────────────────────────────────────────────────────────

def build_schema(cur, selected: set[str]):
    """(Re)create the schema.

    Tables in `selected` are dropped and recreated fresh (so their loaders
    fully rebuild them). Tables not selected are left untouched, but created
    empty if they don't exist yet so the `evaluation` view can always be built.
    The view is always recreated.
    """
    cur.execute("DROP VIEW IF EXISTS evaluation")
    for table in ALL_TABLES:
        create_sql = TABLE_SCHEMAS[table]
        if table in selected:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            cur.executescript(create_sql)
        else:
            # keep existing data; ensure it exists so the view can be built
            cur.executescript(create_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1))
    cur.executescript(VIEW_SCHEMA)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Step 5: consolidate results into SQLite")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Output DB path (default: {DEFAULT_DB})")
    parser.add_argument("--repo", help="Specific repo name (default: all)")
    parser.add_argument(
        "--tables", nargs="+", choices=ALL_TABLES, metavar="TABLE",
        help="Only (re)build these tables, e.g. --tables sonar_results. "
             f"Choices: {', '.join(ALL_TABLES)}. Default: all. "
             "Unlisted tables keep their existing data.",
    )
    args = parser.parse_args()

    repos = [args.repo] if args.repo else sorted(
        d for d in os.listdir(REPOS_DIR) if os.path.isdir(os.path.join(REPOS_DIR, d))
    )
    selected = set(args.tables) if args.tables else set(ALL_TABLES)

    if "human_evaluation" in selected:
        global HUMAN_EVAL_PATH_BY_REPO
        HUMAN_EVAL_PATH_BY_REPO = build_human_eval_index()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    build_schema(cur, selected)

    n_repos = n_test = n_sonar = n_gen = n_human = 0
    for repo in repos:
        repo_dir = os.path.join(REPOS_DIR, repo)
        if not os.path.isdir(repo_dir):
            print(f"[WARN] {repo} not found, skipping")
            continue

        n_repos += 1
        parts = []
        if "repos" in selected:
            insert_repo(cur, repo)
        if "generation_runs" in selected:
            gen_rows = insert_generation_runs(cur, repo, repo_dir)
            n_gen += gen_rows
            parts.append(f"{gen_rows} gen")
        if "test_results" in selected:
            results_path = os.path.join(repo_dir, "results.json")
            if not os.path.isfile(results_path):
                print(f"  [WARN] {repo}: results.json missing — test_results "
                      "will be rebuilt with 0 rows for this repo")
            test = load_json(results_path)
            insert_test_results(cur, repo, test)
            n_test += len(test or {})
            parts.append(f"{len(test or {})} test")
        if "sonar_results" in selected:
            sonar_path = os.path.join(repo_dir, "sonar_results.json")
            if not os.path.isfile(sonar_path):
                print(f"  [WARN] {repo}: sonar_results.json missing — sonar_results "
                      "will be rebuilt with 0 rows for this repo")
            sonar = load_json(sonar_path)
            insert_sonar_results(cur, repo, sonar)
            n_sonar += len(sonar or {})
            parts.append(f"{len(sonar or {})} sonar")
        if "human_evaluation" in selected:
            human_rows = insert_human_evaluation(cur, repo)
            n_human += human_rows
            parts.append(f"{human_rows} human")

        print(f"=== {repo}: " + ", ".join(parts))

    conn.commit()
    conn.close()

    print(f"\nWrote {args.db} (tables rebuilt: {', '.join(sorted(selected))})")
    print(f"  repos processed: {n_repos}")
    if "generation_runs" in selected:
        print(f"  generation_runs: {n_gen}")
    if "test_results" in selected:
        print(f"  test_results:    {n_test}")
    if "sonar_results" in selected:
        print(f"  sonar_results:   {n_sonar}")
    if "human_evaluation" in selected:
        print(f"  human_evaluation: {n_human}")


if __name__ == "__main__":
    main()
