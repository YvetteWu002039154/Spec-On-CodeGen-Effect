"""
Step 3 — Run generated tests and compute pass@1 metrics.

Usage:
    python step3_passatk.py                     # all repos
    python step3_passatk.py --repo ecopeque__new_banking_system
    python step3_passatk.py --repo foo --condition nl
    python step3_passatk.py --repo foo --models claude gpt

Discovers test files at:
    thesis_repos/<repo>/nl/tests/test_<model>.py
    thesis_repos/<repo>/uml/tests/test_<model>.py

Writes per repo:
    thesis_repos/<repo>/results.json

Format of results.json:
    {
      "nl/claude": { "total": N, "passed": N, "failed": N,
                     "failed_tests": [...], "pass_at_1_rate": 0.xx,
                     "strict_pass_at_1": 0|1 },
      ...
    }
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

THESIS_REPOS = os.path.join(os.path.dirname(__file__), "thesis_repos")


def _find_python_with_pytest() -> str:
    """Return the Python executable that has pytest installed."""
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

CONDITIONS = ("nl", "uml")

# Models whose test files we look for; extends automatically to any test_*.py found
DEFAULT_MODELS = ("claude", "gpt", "gemini", "deepseek")


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_pytest(test_file: Path) -> dict:
    """
    Run a single test file with pytest and return a result dict with keys:
        total, passed, failed, failed_tests
    Uses --junit-xml (built into pytest) to parse structured results.
    """
    with tempfile.NamedTemporaryFile(
        suffix=".xml", delete=False, mode="w"
    ) as tmp:
        report_path = tmp.name

    try:
        proc = subprocess.run(
            [
                _PYTHON,
                "-m",
                "pytest",
                str(test_file),
                "--tb=short",
                "-q",
                f"--junit-xml={report_path}",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
            print(f"    [pytest stdout]\n{proc.stdout[-2000:]}", file=sys.stderr)
            print(f"    [pytest stderr]\n{proc.stderr[-1000:]}", file=sys.stderr)
            return {"total": 0, "passed": 0, "failed": 0, "failed_tests": ["COLLECTION_ERROR"]}

        tree = ET.parse(report_path)
        root = tree.getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        if suite is None:
            return {"total": 0, "passed": 0, "failed": 0, "failed_tests": ["PARSE_ERROR"]}

        total = int(suite.get("tests", 0))
        failures = int(suite.get("failures", 0))
        errors = int(suite.get("errors", 0))
        failed = failures + errors
        passed = total - failed

        failed_tests = [
            tc.get("name", "unknown")
            for tc in suite.findall("testcase")
            if tc.find("failure") is not None or tc.find("error") is not None
        ]

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "failed_tests": failed_tests,
        }

    except subprocess.TimeoutExpired:
        return {"total": 0, "passed": 0, "failed": 0, "failed_tests": ["TIMEOUT"]}
    finally:
        if os.path.exists(report_path):
            os.unlink(report_path)


# ---------------------------------------------------------------------------
# Per-repo evaluation
# ---------------------------------------------------------------------------

def evaluate_repo(
    repo_dir: Path,
    conditions: list[str],
    model_filter: list[str] | None,
) -> dict:
    results: dict[str, dict] = {}

    for condition in conditions:
        tests_dir = repo_dir / condition / "tests"
        if not tests_dir.is_dir():
            continue

        # Discover test files: test_<model>.py (skip __init__.py and stubs)
        test_files = sorted(
            f for f in tests_dir.glob("test_*.py")
            if f.stat().st_size > 100  # skip stub files
        )

        for test_file in test_files:
            model_key = test_file.stem[len("test_"):]  # strip "test_" prefix

            if model_filter and model_key not in model_filter:
                continue

            label = f"{condition}/{model_key}"
            print(f"  Running {label} ...")

            raw = run_pytest(test_file)
            total = raw["total"]
            passed = raw["passed"]
            failed = raw["failed"]
            failed_tests = raw["failed_tests"]

            if total == 0:
                pass_rate = 0.0
            else:
                pass_rate = round(passed / total, 4)

            results[label] = {
                "total": total,
                "passed": passed,
                "failed": failed,
                "failed_tests": failed_tests,
                "pass_at_1_rate": pass_rate,
                "strict_pass_at_1": 1 if failed == 0 and total > 0 else 0,
            }

            status = "✓" if failed == 0 else "✗"
            print(f"    {status} {label}  {passed}/{total} passed")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _find_repos(thesis_repos: str) -> list[str]:
    return sorted(
        d for d in os.listdir(thesis_repos)
        if os.path.isdir(os.path.join(thesis_repos, d)) and not d.startswith(".")
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run generated tests and compute pass@1 for thesis repos."
    )
    parser.add_argument(
        "--repo",
        metavar="FOLDER_NAME",
        help="Evaluate a single repo folder. Omit to evaluate all repos.",
    )
    parser.add_argument(
        "--condition",
        choices=["nl", "uml", "both"],
        default="both",
        help="Which condition to evaluate (default: both)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        metavar="MODEL",
        help="Filter by model names (default: all discovered test files)",
    )
    args = parser.parse_args()

    conditions = ["nl", "uml"] if args.condition == "both" else [args.condition]

    if args.repo:
        repo_dirs = [Path(THESIS_REPOS) / args.repo]
    else:
        repo_dirs = [
            Path(THESIS_REPOS) / name
            for name in _find_repos(THESIS_REPOS)
        ]

    all_results: dict[str, dict] = {}

    for repo_dir in repo_dirs:
        if not repo_dir.is_dir():
            print(f"ERROR: {repo_dir} does not exist", file=sys.stderr)
            continue

        print(f"\n→ {repo_dir.name}")
        results = evaluate_repo(repo_dir, conditions, args.models)

        if not results:
            print("  No test files found — run step2 first.")
            continue

        results_path = repo_dir / "results.json"
        results_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  Saved → {results_path.relative_to(Path(THESIS_REPOS).parent)}")

        all_results[repo_dir.name] = results

    if all_results:
        print("\n=== Summary ===")
        for repo_name, repo_results in all_results.items():
            print(f"\n{repo_name}")
            for label, r in repo_results.items():
                rate = r["pass_at_1_rate"]
                strict = r["strict_pass_at_1"]
                print(
                    f"  {label:<20}  {r['passed']:>2}/{r['total']:<2}  "
                    f"pass@1={rate:.4f}  strict={strict}"
                )


if __name__ == "__main__":
    main()
