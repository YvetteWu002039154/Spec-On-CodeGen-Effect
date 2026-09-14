"""Shared internals for the step3 conformance scorers."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPOS_DIR = Path(__file__).resolve().parent / "repos"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Test names are canonical: a single [...] block holding exactly the impl id.
#   test_xxx[nl/claude]
#   test_xxx[uml/gpt]
# A suite must NOT @parametrize a test that uses the impl fixture — that appends
# "-<value>" inside the brackets. Write one test per value instead (see
# test_uses_named_dependency_<dep> in the nl suites). The "-" branch below still
# parses such ids, but cannot tell them from a model name containing "-".

_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]\s*$")
_IMPL_HEAD_RE = re.compile(r"^((?:nl|uml)/[A-Za-z0-9_]+)(?:-|$)")


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

def run_conformance_suite(
    tests_dir: Path, timeout: int = 120, run: int = 0
) -> ET.ElementTree | None:
    """Run pytest on the conformance suite and return the parsed junit tree.

    `run` reaches the suite as RUN in the child's environment only — each
    track's loader.py reads it to pick <model>.run<N>.py. Nothing in this
    process's own environment is touched, so RUN never leaks across calls.
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
            env={**os.environ, "RUN": str(run)},
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
    orphan_broken: list[str] = []

    for suite in suites:
        if suite is None:
            continue
        for tc in suite.findall("testcase"):
            name = tc.get("name", "")
            broken = tc.find("failure") is not None or tc.find("error") is not None
            impl_id = _impl_id_of(name)
            if impl_id is None:
                # Un-parameterized test, or a name we can't attribute to an impl.
                # A *broken* one is never benign: a collection error (module-level
                # import blowing up) is reported against the file, not a
                # parameterized test, so it has no [impl_id] and would otherwise
                # vanish here — leaving the suite silently scored as zero tests.
                if broken:
                    orphan_broken.append(name)
                continue

            slot = per_impl.setdefault(impl_id, {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "failed_tests": [],
            })
            slot["total"] += 1

            if broken:
                slot["failed"] += 1
                slot["failed_tests"].append(name)
            elif tc.find("skipped") is not None:
                slot["skipped"] += 1
            else:
                slot["passed"] += 1

    if orphan_broken:
        print(
            f"  ⚠ {len(orphan_broken)} test(s) failed/errored but carry no [impl_id] — "
            f"likely a collection error, so the suite did NOT run and these scores "
            f"are not trustworthy: {', '.join(orphan_broken[:5])}",
            file=sys.stderr,
        )

    for slot in per_impl.values():
        total = slot["total"]
        completed = slot["passed"] + slot["failed"]
        slot["test_case_pass_rate"] = round(slot["passed"] / total, 4) if total else 0.0
        slot["coverage_rate"] = round(completed / total, 4) if total else 0.0
        slot["pass_at_1"] = 1 if total and slot["passed"] == total else 0

    return per_impl


# ---------------------------------------------------------------------------
# Per-repo evaluation
# ---------------------------------------------------------------------------

def track_suite(repo_dir: Path, track: str) -> Path:
    return repo_dir / track / "tests" / "test_conformance.py"


def evaluate_repo(repo_dir: Path, track: str, timeout: int = 120) -> dict:
    """Score one track's suite against run0 and return {impl_id: slot}.

    Impls with no run0 generation (or a timed-out suite) are absent from the
    result.
    """
    print(f"  Running {track}/tests suite (run0) ...")
    slots = score_runs(repo_dir, track, [0], timeout=timeout)
    return {impl_id: runs[0] for impl_id, runs in slots.items() if runs[0] is not None}


def score_runs(
    repo_dir: Path,
    track: str,
    runs,
    timeout: int = 120,
    tests_dir: Path | None = None,
) -> dict[str, list]:
    """Score one track's suite once per generation run index in `runs`.

    Each track's loader.py picks its generation from RUN in the pytest child's
    environment (<repo>/<track>/outputcode/<model>.run<N>.py), so re-scoring a
    different generation is the same suite re-run with a different `run` — no
    file shuffling and nothing written under repos/.

    Returns {impl_id: [slot_or_None, ...]} positionally aligned with `runs`;
    a slot is aggregate()'s per-impl dict, or None if that run did not produce
    one (generation missing, or the suite timed out).

    `tests_dir` overrides <repo>/<track>/tests. Reports/variance_pilot keeps its
    own copy of the suite — same contract, but driven by per-(model, run) drivers
    instead of the main study's run0-only ones — and points here at that copy.

    Single definition of "resample a cell" for every caller that needs more
    than one generation: step3_structural_fidelity's 10-run average, and both
    Reports/variance_pilot scripts.
    """
    tests_dir = tests_dir or repo_dir / track / "tests"
    per_impl: dict[str, list] = {}
    for run in runs:
        tree = run_conformance_suite(tests_dir, timeout=timeout, run=run)
        agg = aggregate(tree) if tree is not None else {}
        for model in MODELS:
            impl_id = f"{track}/{model}"
            per_impl.setdefault(impl_id, []).append(agg.get(impl_id))
    return per_impl


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def has_suite(d: Path, tracks: tuple[str, ...] = ("nl", "uml")) -> bool:
    return (
        any(track_suite(d, t).exists() for t in tracks)
        or (d / "tests" / "test_conformance.py").exists()
    )


def find_repos(tracks: tuple[str, ...] = ("nl", "uml")) -> list[str]:
    return sorted(
        d.name for d in REPOS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".") and has_suite(d, tracks)
    )


# ---------------------------------------------------------------------------
# results.json — merge-on-write
# ---------------------------------------------------------------------------

def write_results_merged(repo_dir: Path, new_results: dict, track: str) -> Path:
    results_path = repo_dir / "results.json"
    existing = {}
    if results_path.exists():
        try:
            existing = json.loads(results_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    def _owned(impl_id: str) -> bool:
        return impl_id.partition("/")[0] == track

    merged = {k: v for k, v in existing.items() if not _owned(k)}
    merged.update(new_results)

    results_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return results_path


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_repo_summary(repo_name: str, results: dict) -> None:
    print(f"\n  {'impl':<16}  {'p/f/s of total':<18}  {'test rate':<9}  pass@1")
    print(f"  {'-'*16}  {'-'*18}  {'-'*9}  ------")
    for impl_id in sorted(results):
        r = results[impl_id]
        counts = f"{r['passed']:>2}/{r['failed']:>2}/{r['skipped']:>2} of {r['total']:<2}"
        print(
            f"  {impl_id:<16}  {counts:<18}  "
            f"{r['test_case_pass_rate']:<9.4f}  {r['pass_at_1']}"
        )
