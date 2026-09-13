"""Step 3a — Functional correctness (NL track only).

Runs each repo's behavioral conformance suite at
    repos/<repo>/nl/tests/test_conformance.py
against the 4 NL generations (parametrize ids like ``nl/claude``).

Single generation per (repo, model) — a COST decision, not a claim that
run-to-run noise is negligible. Unlike the UML suite (adapter-free reflection,
so resampling is free), every NL generation needs a hand-written driver, so
averaging N runs would need N x 48 drivers instead of 48.

What the pilot actually measured (Reports/variance_pilot/, analysis.ipynb SS2.1):
scored under BOTH NL instruments, the within-cell/between-model SD ratio is
  Inventory-Management  generic 0.21   per-generation 0.90
  new_banking_system    generic 1.19   per-generation 1.00  (near ceiling: cell
                                       mean 0.99, so almost no signal AND almost
                                       no noise — ratio uninformative)
The generic driver UNDERSTATES variance because its misses are correlated across
runs, and on Inventory-Management it also mis-ranks the models (gpt 0.40 vs 0.85
— three of its four generations name classes in Portuguese, invisible to the
driver's English keyword search). So run-to-run noise is NOT small relative to
the model differences reported here; single-run values carry that uncertainty
and should be read with it. See the thesis threats-to-validity section.

The loader picks ``nl/outputcode/<model>.run<RUN>.py``, RUN defaulting to "0";
set RUN=<n> to score a different run. ADAPTER=per_generation selects the
hand-written drivers where they exist (the two pilot repos).

Why a separate script from UML (step3_structural_fidelity.py), not just a
--condition flag: the two tracks are different instruments (behavioral vs
structural) with different sampling rules established independently (NL is
settled at single-run; UML's sampling is still under review, see
Reports/variance_pilot/structural_fidelity.py) — keeping them as separate
CLIs keeps each track's own assumptions from leaking into the other's.

Usage:
    python step3_functional_correctness.py                  # all repos
    python step3_functional_correctness.py --repo Twiddllo__NexusCtrl
    python step3_functional_correctness.py --repo foo --models claude gpt

Writes/merges per repo (touches only nl/* and reference keys — see
step3_common.write_results_merged):
    repos/<repo>/results.json

results.json format, per impl id — see step3_common.aggregate():
    "nl/claude": { "total": N, "passed": p, "failed": f, "skipped": s,
                   "failed_tests": [...],
                   "test_case_pass_rate": passed / total,   # continuous, partial credit
                   "coverage_rate": (passed + failed) / total,
                   "pass_at_1": 1 if passed == total else 0 }   # Chen et al. pass@1
"""

import argparse
import sys

from step3_common import REPOS_DIR, evaluate_repo, find_repos, print_repo_summary, \
    write_results_merged

CONDITIONS = ["nl"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the NL behavioral conformance suite and compute functional-correctness "
                     "pass@1 across thesis repos."
    )
    parser.add_argument(
        "--repo", metavar="FOLDER_NAME",
        help="Evaluate a single repo folder. Omit to evaluate all repos with an nl/tests suite.",
    )
    parser.add_argument(
        "--models", nargs="+", default=None, metavar="MODEL",
        help="Filter by model names, e.g. --models claude gpt (default: all).",
    )
    parser.add_argument(
        "--timeout", type=int, default=120, metavar="SECONDS",
        help="Per-suite pytest timeout in seconds (default: 120).",
    )
    args = parser.parse_args()

    if args.repo:
        repo_dirs = [REPOS_DIR / args.repo]
    else:
        repo_dirs = [REPOS_DIR / name for name in find_repos(tracks=("nl",))]

    all_results: dict[str, dict] = {}

    for repo_dir in repo_dirs:
        if not repo_dir.is_dir():
            print(f"ERROR: {repo_dir} does not exist", file=sys.stderr)
            continue

        print(f"\n→ {repo_dir.name}")
        results = evaluate_repo(repo_dir, CONDITIONS, args.models, timeout=args.timeout)
        if not results:
            continue

        results_path = write_results_merged(repo_dir, results, CONDITIONS)
        print(f"  Saved → {results_path.relative_to(REPOS_DIR.parent)}")
        print_repo_summary(repo_dir.name, results)

        all_results[repo_dir.name] = results

    if len(all_results) > 1:
        print("\n=== Cross-repo summary (functional correctness, NL) ===")
        for repo_name, repo_results in all_results.items():
            print(f"\n{repo_name}")
            for impl_id in sorted(repo_results):
                r = repo_results[impl_id]
                print(
                    f"  {impl_id:<16}  test_rate={r['test_case_pass_rate']:.4f}  "
                    f"pass@1={r['pass_at_1']}  "
                    f"(skipped={r['skipped']}/{r['total']})"
                )


if __name__ == "__main__":
    main()
