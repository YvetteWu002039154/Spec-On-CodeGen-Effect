"""Step 3a — Functional correctness (NL track only).

Usage:
    python step3_functional_correctness.py      # all repos, all models

results.json format, per impl id — see step3_common.aggregate():
    "nl/claude": { "total": N, "passed": p, "failed": f, "skipped": s,
                   "failed_tests": [...],
                   "test_case_pass_rate": passed / total,   # continuous, partial credit
                   "coverage_rate": (passed + failed) / total,
                   "pass_at_1": 1 if passed == total else 0 }   # Chen et al. pass@1
"""

from step3_common import REPOS_DIR, evaluate_repo, find_repos, print_repo_summary, write_results_merged

TRACK = "nl"
TIMEOUT = 120  # per-suite pytest timeout, seconds


def main() -> None:
    all_results: dict[str, dict] = {}

    for repo_name in find_repos(tracks=(TRACK,)):
        repo_dir = REPOS_DIR / repo_name
        print(f"\n→ {repo_name}")

        results = evaluate_repo(repo_dir, TRACK, timeout=TIMEOUT)
        if not results:
            continue

        results_path = write_results_merged(repo_dir, results, TRACK)
        print(f"  Saved → {results_path.relative_to(REPOS_DIR.parent)}")
        print_repo_summary(repo_name, results)

        all_results[repo_name] = results

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
