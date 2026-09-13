"""Shared internals for the step3 conformance scorers.

Track-agnostic: parses/runs pytest, aggregates JUnit XML into per-impl tallies,
and merges results into each repo's results.json. Used by the two track
scripts, step3_functional_correctness.py (NL) and step3_structural_fidelity.py
(UML). This module is a library only — it has no CLI of its own.

See step3_functional_correctness.py / step3_structural_fidelity.py for why the
two tracks are separate scripts, not just a --condition flag: they are
different instruments (behavioral vs structural) with different sampling
rules (NL scores a single generation; UML's sampling is under review — see
Reports/variance_pilot/structural_fidelity.py), so keeping them as
separate CLIs makes each track's assumptions explicit instead of hidden
behind a shared flag.
"""

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
        slot["test_case_pass_rate"] = round(slot["passed"] / total, 4) if total else 0.0
        slot["coverage_rate"] = round(completed / total, 4) if total else 0.0
        slot["pass_at_1"] = 1 if total and slot["passed"] == total else 0

    return per_impl


# ---------------------------------------------------------------------------
# Per-repo evaluation
# ---------------------------------------------------------------------------

def track_suite(repo_dir: Path, track: str) -> Path:
    return repo_dir / track / "tests" / "test_conformance.py"


def evaluate_repo(
    repo_dir: Path,
    conditions: list[str],
    model_filter: list[str] | None,
    timeout: int = 120,
) -> dict:
    """Run the conformance suite(s) for `conditions` and return {impl_id: slot}."""
    results: dict[str, dict] = {}
    ran_any = False

    # Per-track packages (nl/tests, uml/tests) — the current layout.
    for track in conditions:
        if track_suite(repo_dir, track).exists():
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


def score_runs(
    repo_dir: Path,
    track: str,
    runs,
    model_filter: list[str] | None = None,
    timeout: int = 120,
    tests_dir: Path | None = None,
) -> dict[str, list]:
    """Score one track's suite once per generation run index in `runs`.

    Each track's loader.py picks its generation from the RUN env var
    (<repo>/<track>/outputcode/<model>.run<N>.py), so re-scoring a different
    generation is the same suite re-run with RUN set — no file shuffling and
    nothing written under repos/.

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
    previous = os.environ.get("RUN")
    try:
        for run in runs:
            os.environ["RUN"] = str(run)
            tree = run_conformance_suite(tests_dir, timeout=timeout)
            agg = aggregate(tree) if tree is not None else {}
            for model in MODELS:
                if model_filter and model not in model_filter:
                    continue
                impl_id = f"{track}/{model}"
                per_impl.setdefault(impl_id, []).append(agg.get(impl_id))
    finally:
        # Restore rather than pop: callers may themselves be running under a
        # deliberate RUN, and clobbering it would silently rescore run0.
        if previous is None:
            os.environ.pop("RUN", None)
        else:
            os.environ["RUN"] = previous
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

def write_results_merged(repo_dir: Path, new_results: dict, conditions: list[str]) -> Path:
    """Merge `new_results` into repo_dir/results.json, touching ONLY the given
    conditions' keys (plus `reference`, which either script may produce via the
    legacy fallback). Keys for the OTHER condition already on disk are kept
    as-is — so running the NL and UML scorers separately never clobbers each
    other's results, unlike a plain overwrite."""
    results_path = repo_dir / "results.json"
    existing = {}
    if results_path.exists():
        try:
            existing = json.loads(results_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    def _owned(impl_id: str) -> bool:
        if impl_id == "reference":
            return True
        cond, _, _ = impl_id.partition("/")
        return cond in conditions

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
    def _sort_key(impl_id: str) -> tuple:
        return (impl_id != "reference", impl_id)

    print(f"\n  {'impl':<16}  {'p/f/s of total':<18}  {'test rate':<9}  pass@1")
    print(f"  {'-'*16}  {'-'*18}  {'-'*9}  ------")
    for impl_id in sorted(results, key=_sort_key):
        r = results[impl_id]
        counts = f"{r['passed']:>2}/{r['failed']:>2}/{r['skipped']:>2} of {r['total']:<2}"
        print(
            f"  {impl_id:<16}  {counts:<18}  "
            f"{r['test_case_pass_rate']:<9.4f}  {r['pass_at_1']}"
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
