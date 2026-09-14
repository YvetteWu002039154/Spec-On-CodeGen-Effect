"""Step 3b — Structural fidelity (UML track only).

Usage:
    python step3_structural_fidelity.py     # all repos, all models, 10-run average

Writes/merges per repo (touches only uml/* keys — see
step3_common.write_results_merged):
    repos/<repo>/results.json

Per impl id (see step3_common.aggregate() for the per-run shape):
    "uml/gpt": { "test_case_pass_rate": mean over the N scored runs,  # continuous
                 "pass_at_1": fraction of those runs fully correct,   # Chen et al.
                                                                      # pass@1, n=N
                 "n_runs_averaged": N,
                 ... (total/passed/failed/skipped/failed_tests from the first
                      scored run, kept for reference — NOT an average) }
"""

from step3_common import REPOS_DIR, find_repos, print_repo_summary, score_runs, write_results_merged

TRACK = "uml"
RUNS = 10      # the settled rule: average structural fidelity over 10 generations
TIMEOUT = 120  # per-suite pytest timeout, seconds


def main() -> None:
    all_results: dict[str, dict] = {}

    for repo_name in find_repos(tracks=(TRACK,)):
        repo_dir = REPOS_DIR / repo_name
        print(f"\n→ {repo_name}")

        per_impl = score_runs(repo_dir, TRACK, range(RUNS), timeout=TIMEOUT)

        results: dict[str, dict] = {}
        for impl_id, slots in sorted(per_impl.items()):
            scored = [s for s in slots if s is not None]
            shown = " ".join("—" if s is None else f"{s['test_case_pass_rate']:.2f}"
                             for s in slots)
            print(f"  {impl_id:<16}  {shown}")
            if not scored:
                continue
            # The first scored run supplies total/passed/failed/skipped/failed_tests
            # for reference; the two rates below are the N-run aggregates.
            rates = [s["test_case_pass_rate"] for s in scored]
            results[impl_id] = {
                **scored[0],
                "test_case_pass_rate": round(sum(rates) / len(rates), 4),
                "pass_at_1": round(sum(1 for r in rates if r == 1.0) / len(rates), 4),
                "n_runs_averaged": len(rates),
            }

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
                f"(skipped={r['skipped']}/{r['total']})"
            )


if __name__ == "__main__":
    main()
