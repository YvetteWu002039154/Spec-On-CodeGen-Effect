"""Step 3b — Structural fidelity (UML track only).

Usage:
    python step3_structural_fidelity.py     # all repos, all models, 10-run average

Writes/merges per repo (touches only uml/* keys — see
step3_common.write_results_merged):
    repos/<repo>/results.json

Per impl id, every count is **pooled over the 10 generations** so the counts and
the rates describe the same thing (a run0-only snapshot next to a 10-run average
is what made `passed=0, failed=10, test_case_pass_rate=0.72` possible):

    "uml/gpt": { "total":   sum of the N scored runs' totals,   # e.g. 10 x 10
                 "passed":  sum over those runs,
                 "failed":  sum over those runs,
                 "skipped": sum over those runs,
                 "test_case_pass_rate": passed / total,         # continuous
                 "coverage_rate": (passed + failed) / total,
                 "pass_at_1": fraction of the N runs fully correct,  # Chen et al.
                                                                     # pass@1, n=N
                 "n_runs_averaged": N,
                 "failed_tests": ["run0: test_x[uml/gpt]", ...],  # ALL runs,
                                                                  # run-labelled
                 "per_run": [ {"run": 0, "scored": true, "total": ..., "passed": ...,
                               "failed": ..., "skipped": ..., "test_case_pass_rate": ...,
                               "pass_at_1": ..., "failed_tests": [...]},
                              {"run": 3, "scored": false},   # missing gen / timeout
                              ... ] }
"""

from step3_common import REPOS_DIR, find_repos, score_runs, write_results_merged, print_repo_summary

TRACK = "uml"
RUNS = 10      # the settled rule: average structural fidelity over 10 generations
TIMEOUT = 120  # per-suite pytest timeout, seconds


def pool(impl_id: str, slots: list) -> dict | None:
    """Pool one cell's per-run slots into a single record.

    `slots` is positionally aligned with range(RUNS); a None means that run
    produced no score (generation missing, or the suite timed out) and is left
    out of every total — it is not counted as a failure.
    """
    per_run = []
    for run, slot in enumerate(slots):
        if slot is None:
            per_run.append({"run": run, "scored": False})
            continue
        per_run.append({
            "run": run,
            "scored": True,
            "total": slot["total"],
            "passed": slot["passed"],
            "failed": slot["failed"],
            "skipped": slot["skipped"],
            "test_case_pass_rate": slot["test_case_pass_rate"],
            "pass_at_1": slot["pass_at_1"],
            "failed_tests": slot["failed_tests"],
        })

    scored = [r for r in per_run if r["scored"]]
    if not scored:
        return None

    total = sum(r["total"] for r in scored)
    passed = sum(r["passed"] for r in scored)
    failed = sum(r["failed"] for r in scored)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": sum(r["skipped"] for r in scored),
        # Pooled, not a mean of per-run rates. The two agree whenever the runs
        # all expose the same number of tests (the normal case); pooling stays
        # consistent with the counts above when one does not.
        "test_case_pass_rate": round(passed / total, 4) if total else 0.0,
        "coverage_rate": round((passed + failed) / total, 4) if total else 0.0,
        "pass_at_1": round(sum(1 for r in scored if r["pass_at_1"] == 1) / len(scored), 4),
        "n_runs_averaged": len(scored),
        "failed_tests": [f"run{r['run']}: {name}"
                         for r in scored for name in r["failed_tests"]],
        "per_run": per_run,
    }


def main() -> None:
    all_results: dict[str, dict] = {}

    for repo_name in find_repos(tracks=(TRACK,)):
        repo_dir = REPOS_DIR / repo_name
        print(f"\n→ {repo_name}")

        per_impl = score_runs(repo_dir, TRACK, range(RUNS), timeout=TIMEOUT)

        results: dict[str, dict] = {}
        for impl_id, slots in sorted(per_impl.items()):
            shown = " ".join("—" if s is None else f"{s['test_case_pass_rate']:.2f}"
                             for s in slots)
            print(f"  {impl_id:<16}  {shown}")
            pooled = pool(impl_id, slots)
            if pooled is not None:
                results[impl_id] = pooled

        if not results:
            continue

        results_path = write_results_merged(repo_dir, results, TRACK)
        print(f"  Saved → {results_path.relative_to(REPOS_DIR.parent)}")
        print_repo_summary(repo_name, results)

        all_results[repo_name] = results

    print("\n=== Cross-repo summary (structural fidelity, UML) ===")
    for repo_name, repo_results in all_results.items():
        print(f"\n{repo_name}")
        for impl_id in sorted(repo_results):
            r = repo_results[impl_id]
            print(
                f"  {impl_id:<16}  test_rate={r['test_case_pass_rate']:.4f}  "
                f"pass@1={r['pass_at_1']}  "
                f"({r['passed']}/{r['total']} over {r['n_runs_averaged']} runs, "
                f"skipped={r['skipped']})"
            )


if __name__ == "__main__":
    main()
