"""
Step 3 — Run the per-repo conformance suites and compute pass@1 per implementation.

Each repo ships one conformance suite PER TRACK:
    thesis_repos/<repo>/nl/tests/test_conformance.py
    thesis_repos/<repo>/uml/tests/test_conformance.py

Each track's suite is parameterized over that track's 4 generated
implementations (no reference), with parametrize ids like ``nl/claude`` /
``uml/gpt``. We run pytest once per track, parse the junit XML, group testcases
by the parametrize id (the bracketed suffix in the test name), and merge the
tracks into one result set per repo. Skips are reported separately from
failures: a skip means the impl lacks a capability (Unsupported adapter), not
that it produced wrong behavior.

Backward compatible: if a repo has no per-track packages, we fall back to a
legacy single suite at ``thesis_repos/<repo>/tests/test_conformance.py`` (which
may still include a ``reference`` row).

Usage:
    python step3_passatk.py                                  # all repos
    python step3_passatk.py --repo Twiddllo__NexusCtrl
    python step3_passatk.py --repo foo --condition nl
    python step3_passatk.py --repo foo --models claude gpt

Writes per repo:
    thesis_repos/<repo>/results.json

results.json format (one entry per impl id):
    {
      "nl/claude":  { "total": N, "passed": p, "failed": f, "skipped": s,
                      "failed_tests": [...],
                      "pass_at_1_rate":  passed / total,        # skips count against you
                      "coverage_rate":   (passed + failed) / total,
                      "strict_pass_at_1": 1 if passed == total else 0 },  # skips & fails both count against
      "uml/gpt":    { ... },
      ...
    }
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

THESIS_REPOS = Path(__file__).resolve().parent / "thesis_repos"

# Test names look like:
#   test_xxx[nl/claude]                       (impl fixture only)
#   test_xxx[nl/claude-params0-True]          (impl fixture + extra @parametrize)
#   test_xxx[reference]
#   test_xxx[reference-params0]
# We grab the LAST [...] block, then extract the impl id prefix.
_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]\s*$")
_IMPL_HEAD_RE = re.compile(r"^(reference|(?:nl|uml)/[A-Za-z0-9_]+)(?:-|$)")


def _impl_id_of(test_name: str) -> str | None:
    bracket = _BRACKET_RE.search(test_name)
    if not bracket:
        return None
    head = _IMPL_HEAD_RE.match(bracket.group(1))
    return head.group(1) if head else None


def _find_python_with_pytest() -> str:
    candidates = [sys.executable, shutil.which("python3"), shutil.which("python")]
    for py in candidates:
        if not py:
            continue
        r = subprocess.run(
            [py, "-m", "pytest", "--version"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            return py
    raise RuntimeError("Cannot find a Python with pytest installed. Run: pip install pytest")


_PYTHON = _find_python_with_pytest()


# ---------------------------------------------------------------------------
# Pytest runner
# ---------------------------------------------------------------------------

def run_conformance_suite(tests_dir: Path, timeout: int = 120) -> ET.ElementTree | None:
    """Run pytest on the conformance suite and return the parsed junit tree.

    Output goes to temp FILES, not pipes: with pipes, any process that inherits
    them (a thread or child spawned by an implementation under test) keeps the
    pipe open and blocks us until the timeout even after pytest itself exits.
    A file descriptor cannot block us. On timeout the whole process group is
    killed so no helper processes linger.
    """
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w") as tmp:
        report_path = tmp.name
    out_file = tempfile.NamedTemporaryFile(suffix=".out", delete=False)

    proc = None
    try:
        proc = subprocess.Popen(
            [
                _PYTHON, "-m", "pytest", str(tests_dir),
                "--tb=short", "-q", "-p", "no:cacheprovider",
                f"--junit-xml={report_path}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=out_file, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"    [pytest TIMEOUT after {timeout}s — killing process group]",
                  file=sys.stderr)
            try:
                os.killpg(proc.pid, 9)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            proc.wait()
            # Surface captured output (incl. any faulthandler stack dump) so a
            # hang is diagnosable instead of silent.
            out_file.flush()
            tail = Path(out_file.name).read_text(errors="replace")[-4000:]
            if tail.strip():
                print(f"    [pytest output before kill]\n{tail}", file=sys.stderr)
            return None

        if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
            out_file.close()
            tail = Path(out_file.name).read_text(errors="replace")[-2000:]
            print(f"    [pytest output]\n{tail}", file=sys.stderr)
            return None

        return ET.parse(report_path)

    finally:
        out_file.close()
        for f in (report_path, out_file.name):
            if os.path.exists(f):
                os.unlink(f)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(tree: ET.ElementTree) -> dict[str, dict]:
    """Group testcases by the [impl_id] suffix in their name and tally outcomes."""
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")

    per_impl: dict[str, dict] = {}

    for suite in suites:
        if suite is None:
            continue
        for tc in suite.findall("testcase"):
            name = tc.get("name", "")
            impl_id = _impl_id_of(name)
            if impl_id is None:
                # Un-parameterized test, or a name we can't attribute to an impl.
                continue

            slot = per_impl.setdefault(impl_id, {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "failed_tests": [],
            })
            slot["total"] += 1

            if tc.find("failure") is not None or tc.find("error") is not None:
                slot["failed"] += 1
                slot["failed_tests"].append(name)
            elif tc.find("skipped") is not None:
                slot["skipped"] += 1
            else:
                slot["passed"] += 1

    for slot in per_impl.values():
        total = slot["total"]
        completed = slot["passed"] + slot["failed"]
        slot["pass_at_1_rate"] = round(slot["passed"] / total, 4) if total else 0.0
        slot["coverage_rate"] = round(completed / total, 4) if total else 0.0
        slot["strict_pass_at_1"] = 1 if total and slot["passed"] == total else 0

    return per_impl


# ---------------------------------------------------------------------------
# Per-repo evaluation
# ---------------------------------------------------------------------------

def _track_suite(repo_dir: Path, track: str) -> Path:
    return repo_dir / track / "tests" / "test_conformance.py"


def evaluate_repo(
    repo_dir: Path,
    conditions: list[str],
    model_filter: list[str] | None,
    timeout: int = 120,
) -> dict:
    results: dict[str, dict] = {}
    ran_any = False

    # Per-track packages (nl/tests, uml/tests) — the current layout.
    for track in conditions:
        if _track_suite(repo_dir, track).exists():
            ran_any = True
            print(f"  Running {track}/tests suite ...")
            tree = run_conformance_suite(repo_dir / track / "tests", timeout=timeout)
            if tree is not None:
                results.update(aggregate(tree))

    # Legacy fallback: one shared suite at <repo>/tests (may include reference).
    if not ran_any:
        legacy = repo_dir / "tests"
        if (legacy / "test_conformance.py").exists():
            print(f"  Running legacy tests/ suite ...")
            tree = run_conformance_suite(legacy, timeout=timeout)
            if tree is not None:
                results.update(aggregate(tree))
        else:
            print(f"  No conformance suite found for {repo_dir.name}")
            return {}

    def _keep(impl_id: str) -> bool:
        if impl_id == "reference":
            return True
        if "/" not in impl_id:
            return True
        cond, _, model = impl_id.partition("/")
        if conditions and cond not in conditions:
            return False
        if model_filter and model not in model_filter:
            return False
        return True

    return {k: v for k, v in results.items() if _keep(k)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _has_suite(d: Path) -> bool:
    return (
        _track_suite(d, "nl").exists()
        or _track_suite(d, "uml").exists()
        or (d / "tests" / "test_conformance.py").exists()
    )


def _find_repos() -> list[str]:
    return sorted(
        d.name for d in THESIS_REPOS.iterdir()
        if d.is_dir() and not d.name.startswith(".") and _has_suite(d)
    )


def _print_repo_summary(repo_name: str, results: dict) -> None:
    def _sort_key(impl_id: str) -> tuple:
        return (impl_id != "reference", impl_id)

    print(f"\n  {'impl':<16}  {'p/f/s of total':<18}  {'pass@1':<8}  strict")
    print(f"  {'-'*16}  {'-'*18}  {'-'*8}  ------")
    for impl_id in sorted(results, key=_sort_key):
        r = results[impl_id]
        counts = f"{r['passed']:>2}/{r['failed']:>2}/{r['skipped']:>2} of {r['total']:<2}"
        print(
            f"  {impl_id:<16}  {counts:<18}  "
            f"{r['pass_at_1_rate']:<8.4f}  {r['strict_pass_at_1']}"
        )

    ref = results.get("reference")
    if ref:
        if ref["failed"] > 0:
            print(f"  ⚠ reference has {ref['failed']} failing test(s) — suite is unsound", file=sys.stderr)
        if ref["passed"] == 0:
            print(
                f"  ⚠ reference passed 0/{ref['total']} (skipped={ref['skipped']}) — "
                f"reference module likely failed to load; downstream pass@1 is meaningless",
                file=sys.stderr,
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run conformance suites and compute pass@1 across thesis repos."
    )
    parser.add_argument(
        "--repo", metavar="FOLDER_NAME",
        help="Evaluate a single repo folder. Omit to evaluate all repos with a conformance suite.",
    )
    parser.add_argument(
        "--condition", choices=["nl", "uml", "both"], default="both",
        help="Filter implementations by condition (default: both).",
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

    conditions = ["nl", "uml"] if args.condition == "both" else [args.condition]

    if args.repo:
        repo_dirs = [THESIS_REPOS / args.repo]
    else:
        repo_dirs = [THESIS_REPOS / name for name in _find_repos()]

    all_results: dict[str, dict] = {}

    for repo_dir in repo_dirs:
        if not repo_dir.is_dir():
            print(f"ERROR: {repo_dir} does not exist", file=sys.stderr)
            continue

        print(f"\n→ {repo_dir.name}")
        results = evaluate_repo(repo_dir, conditions, args.models, timeout=args.timeout)
        if not results:
            continue

        results_path = repo_dir / "results.json"
        results_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  Saved → {results_path.relative_to(THESIS_REPOS.parent)}")
        _print_repo_summary(repo_dir.name, results)

        all_results[repo_dir.name] = results

    if len(all_results) > 1:
        print("\n=== Cross-repo summary ===")
        for repo_name, repo_results in all_results.items():
            print(f"\n{repo_name}")
            for impl_id in sorted(repo_results):
                r = repo_results[impl_id]
                print(
                    f"  {impl_id:<16}  pass@1={r['pass_at_1_rate']:.4f}  "
                    f"strict={r['strict_pass_at_1']}  "
                    f"(skipped={r['skipped']}/{r['total']})"
                )


if __name__ == "__main__":
    main()
