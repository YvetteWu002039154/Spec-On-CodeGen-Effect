"""Step 3b — Structural fidelity (UML track only).

Runs each repo's structural conformance suite at
    repos/<repo>/uml/tests/test_conformance.py
against the 4 UML generations (parametrize ids like ``uml/gpt``). The suite is
adapter-free reflection (structure.py uses inspect/ast directly, name-tolerant),
so — unlike NL — it needs no per-model driver code to resample.

SAMPLING RULE — SETTLED (2026-09-05): average over 10 generations, NOT NL's
single-run rule. Reports/variance_pilot/structural_fidelity.py scored all
12 repos across their 10 existing per-run generations and found within-cell
run-to-run SD ~1.0x the between-model SD — i.e. run noise is as large as the
model differences the study measures. Two real harness bugs were found and
fixed along the way (both confirmed NOT to be model defects):
  - hackstarsj__.../uml/tests/loader.py never bootstrapped Django (unlike
    jobic10's/kapitoshk4's loaders) — a generation that correctly imported
    django.db.models crashed on load for that reason alone.
  - hackstarsj__.../uml/tests/structure.py's field/reference checker only read
    __annotations__ — invisible to real Django model fields (plain class-body
    assignments) — so a correct Django generation could load fine and still
    fail every structural test. Ported the _meta.get_fields()-based Django
    field/relation detection already used by jobic10's/kapitoshk4's checkers.
Re-running the variance check after BOTH fixes still gave ~1.05x, confirming
the ratio is real and repo-general, not an artifact of those two bugs — so
this script now averages by default, matching the internal-quality rule.

Why a separate script from NL (step3_functional_correctness.py): see that
script's docstring — different instruments, independently-decided sampling
rules, kept from leaking into each other.

Usage:
    python step3_structural_fidelity.py                       # all repos, 10-run average (default)
    python step3_structural_fidelity.py --repo Twiddllo__NexusCtrl
    python step3_structural_fidelity.py --repo foo --models claude gpt
    python step3_structural_fidelity.py --repo foo --runs 3           # average over 3 runs instead
    python step3_structural_fidelity.py --repo foo --single-run       # legacy: run0 only, no
                                                                       # averaging (debugging/comparison)

Writes/merges per repo (touches only uml/* and reference keys — see
step3_common.write_results_merged):
    repos/<repo>/results.json

Averaged results.json fields, per impl id (see step3_common.aggregate() for
the un-averaged per-run shape):
    "uml/gpt": { "test_case_pass_rate": mean over N runs,       # continuous
                 "pass_at_1": fraction of N runs fully correct, # Chen et al. pass@1
                                                                 # estimator with n=N samples
                 "n_runs_averaged": N,
                 ... (total/passed/failed/skipped/failed_tests from run0, kept
                      for reference — NOT meaningful as an average) }
"""

import argparse
import sys

from step3_common import REPOS_DIR, evaluate_repo, find_repos, print_repo_summary, \
    write_results_merged, score_runs

CONDITIONS = ["uml"]
DEFAULT_RUNS = 10


def _score_multi_run(repo_dir, n_runs: int, model_filter, timeout: int) -> dict:
    """Run the uml suite once per RUN in 0..n_runs-1; return {impl_id: [rate, ...]}."""
    per_impl = score_runs(repo_dir, "uml", range(n_runs), model_filter, timeout=timeout)
    return {impl_id: [None if slot is None else slot["test_case_pass_rate"] for slot in slots]
            for impl_id, slots in per_impl.items()}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the UML structural conformance suite and compute structural-fidelity "
                     "pass@1 across thesis repos, averaged over multiple generations (default: 10)."
    )
    parser.add_argument(
        "--repo", metavar="FOLDER_NAME",
        help="Evaluate a single repo folder. Omit to evaluate all repos with a uml/tests suite.",
    )
    parser.add_argument(
        "--models", nargs="+", default=None, metavar="MODEL",
        help="Filter by model names, e.g. --models claude gpt (default: all).",
    )
    parser.add_argument(
        "--timeout", type=int, default=120, metavar="SECONDS",
        help="Per-suite pytest timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "--runs", type=int, default=DEFAULT_RUNS, metavar="N",
        help=f"Average over N per-run generations (default: {DEFAULT_RUNS}, the settled rule — "
             "see module docstring).",
    )
    parser.add_argument(
        "--single-run", action="store_true",
        help="Legacy behavior: score only RUN (default run0), no averaging. For debugging/comparison "
             "against the pre-2026-09-05 pipeline, not for the main study.",
    )
    args = parser.parse_args()

    if args.repo:
        repo_dirs = [REPOS_DIR / args.repo]
    else:
        repo_dirs = [REPOS_DIR / name for name in find_repos(tracks=("uml",))]

    all_results: dict[str, dict] = {}

    for repo_dir in repo_dirs:
        if not repo_dir.is_dir():
            print(f"ERROR: {repo_dir} does not exist", file=sys.stderr)
            continue

        print(f"\n→ {repo_dir.name}")

        if args.single_run:
            results = evaluate_repo(repo_dir, CONDITIONS, args.models, timeout=args.timeout)
        else:
            per_impl_rates = _score_multi_run(repo_dir, args.runs, args.models, args.timeout)
            for impl_id, rates in sorted(per_impl_rates.items()):
                shown = " ".join("—" if r is None else f"{r:.2f}" for r in rates)
                print(f"  {impl_id:<16}  {shown}")

            # run0's slot supplies total/passed/failed/skipped/failed_tests for reference;
            # test_case_pass_rate/pass_at_1 are overwritten with the N-run average below.
            results = evaluate_repo(repo_dir, CONDITIONS, args.models, timeout=args.timeout)
            for impl_id, rates in per_impl_rates.items():
                vals = [r for r in rates if r is not None]
                if impl_id in results and vals:
                    results[impl_id]["test_case_pass_rate"] = round(sum(vals) / len(vals), 4)
                    results[impl_id]["pass_at_1"] = round(
                        sum(1 for v in vals if v == 1.0) / len(vals), 4)
                    results[impl_id]["n_runs_averaged"] = len(vals)

        if not results:
            continue

        results_path = write_results_merged(repo_dir, results, CONDITIONS)
        print(f"  Saved → {results_path.relative_to(REPOS_DIR.parent)}")
        print_repo_summary(repo_dir.name, results)

        all_results[repo_dir.name] = results

    if len(all_results) > 1:
        print("\n=== Cross-repo summary (structural fidelity, UML) ===")
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
