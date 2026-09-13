"""Run-to-run variance of FUNCTIONAL CORRECTNESS (NL track).

Scores runs 0..N-1 of the NL generations ALREADY on disk at
    repos/<repo>/nl/outputcode/<model>.run<N>.py
through that repo's own live suite at repos/<repo>/nl/tests/.

Run:  ../../.venv/bin/python functional_correctness.py
      ../../.venv/bin/python functional_correctness.py --repo vstorm --runs 4

Writes one row per (repo, condition, model, run) into results.db's variance_pilot
table.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                        # POC-v1/
sys.path.insert(0, str(ROOT))

from step3_common import MODELS, REPOS_DIR, score_runs   # noqa: E402
from step5_build_db import DB_PATH, write_variance_pilot  # noqa: E402

TRACK = "nl"
N_RUNS = 4          # score runs 0..3
TIMEOUT = 180       # seconds per suite invocation
PILOT_REPOS = [
    "nishant0820__Inventory-Management-System",   # Tk + sqlite desktop CRUD
    "ecopque__new_banking_system",               # plain in-memory Python
]
ADAPTER = "per_generation"


def _check_copies(repo) -> None:
    """The pilot keeps its own copy of loader.py and test_conformance.py.
    Copies rot: the previous pilot suite drifted from the repo's and silently
    scored a stale contract. So verify them here and fail loudly instead.

    test_conformance.py is allowed to differ on exactly one line — the import
    that selects adapter_per_run instead of adapter — and loader.py on the block
    that redirects to the main tree's outputcode/. Anything else is drift.

    adapter_harness/ is NOT copied: adapter_per_run imports the machinery from
    the repo's own adapter.py, which already puts adapter_harness on sys.path,
    so there is one faketk.py and nothing to keep in sync.
    """
    main = REPOS_DIR / repo / TRACK / "tests"
    mine = HERE / repo
    problems = []

    a = (main / "test_conformance.py").read_text().replace(
        "from adapter import build_driver", "from adapter_per_run import build_driver")
    if a != (mine / "test_conformance.py").read_text():
        problems.append("test_conformance.py differs beyond the adapter import")

    if problems:
        raise SystemExit(f"pilot suite for {repo} has drifted:\n  " + "\n  ".join(problems)
                         + "\nRe-copy from the repo, or reconcile deliberately.")


def main() -> None:
    rows = []
    for repo in PILOT_REPOS:
        _check_copies(repo)
        repo_dir = REPOS_DIR / repo
        suite = HERE / repo                       # the pilot's own copy
        if not (suite / "test_conformance.py").exists():
            print(f"ERROR: no pilot suite at {suite}", file=sys.stderr)
            continue

        print(f"\n=== {repo} (runs 0..{N_RUNS - 1}) ===")
        per_impl = score_runs(repo_dir, TRACK, range(N_RUNS), timeout=TIMEOUT,
                              tests_dir=suite)

        for model in MODELS:
            slots = per_impl.get(f"{TRACK}/{model}", [])
            shown = " ".join("—" if s is None else f"{s['test_case_pass_rate']:.2f}"
                             for s in slots)
            print(f"  {model:10s} {shown}")
            for run, slot in enumerate(slots):
                rows.append({
                    "repo": repo, "condition": TRACK, "adapter": ADAPTER,
                        "model": model, "run": run,
                    "test_case_pass_rate": None if slot is None else slot["test_case_pass_rate"],
                    "passed": None if slot is None else slot["passed"],
                    "failed": None if slot is None else slot["failed"],
                    "skipped": None if slot is None else slot["skipped"],
                    "total": None if slot is None else slot["total"],
                    "pass_at_1": None if slot is None else slot["pass_at_1"],
                    "failed_tests": None if slot is None else json.dumps(slot["failed_tests"]),
                })

    n = write_variance_pilot(rows, DB_PATH)
    print(f"\nWrote {n} rows -> {DB_PATH} (variance_pilot, condition='{TRACK}')")


if __name__ == "__main__":
    main()
