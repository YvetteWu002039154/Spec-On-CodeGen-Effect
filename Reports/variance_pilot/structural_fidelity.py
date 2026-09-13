"""Run-to-run variance of STRUCTURAL FIDELITY (UML track).

Same question as functional_correctness.py, asked of the other instrument: is a
single generation representative, or does run noise rival the between-model
differences the study reports?

Scores runs 0..N-1 of the UML generations ALREADY on disk at
    repos/<repo>/uml/outputcode/<model>.run<N>.py
through each repo's live suite at repos/<repo>/uml/tests/, selected by the
RUN env var. Nothing is generated or written under repos/.

Coverage differs from the NL side: the UML suite is adapter-free (structure.py is
pure reflection/AST via inspect + ast, name-tolerant, driving nothing), so it
scores any generation generically — no per-model driver to hand-write. Every repo
with a uml/tests suite is therefore in scope, across all 10 generations, rather
than the NL side's two-repo pilot.

The answer this produced (2026-09-05): within-cell SD ~1.0x the between-model SD,
so a single UML run is NOT representative — which is why
step3_structural_fidelity.py averages 10 runs while
step3_functional_correctness.py still scores one. See that script's docstring for
the two harness bugs found and fixed while establishing this.

Run:  ../../.venv/bin/python structural_fidelity.py
      ../../.venv/bin/python structural_fidelity.py --repo Twiddllo --runs 10

Writes one row per (repo, condition, model, run) into results.db's variance_pilot
table (see step5_build_db.write_variance_pilot). Read back in
Reports/analysis.ipynb SS2.2.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                        # POC-v1/
sys.path.insert(0, str(ROOT))

from step3_common import MODELS, REPOS_DIR, find_repos, score_runs  # noqa: E402
from step5_build_db import DB_PATH, write_variance_pilot             # noqa: E402

TRACK = "uml"
N_RUNS = 10         # score runs 0..9
TIMEOUT = 180       # seconds per suite invocation


def main() -> None:
    repos = find_repos(tracks=(TRACK,))
    rows = []
    for repo in repos:
        print(f"\n=== {repo} ({TRACK}, runs 0..{N_RUNS - 1}) ===")
        per_impl = score_runs(REPOS_DIR / repo, TRACK, range(N_RUNS), timeout=TIMEOUT)

        for model in MODELS:
            slots = per_impl.get(f"{TRACK}/{model}", [])
            shown = " ".join("—" if s is None else f"{s['test_case_pass_rate']:.2f}"
                             for s in slots)
            print(f"  {model:10s} {shown}")
            for run, slot in enumerate(slots):
                rows.append({
                    "repo": repo, "condition": TRACK, "adapter": "reflection",
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
