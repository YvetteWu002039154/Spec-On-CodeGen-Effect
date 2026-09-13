"""
Usage:
    python step4_sonarqube.py
 
An A/B over every such run confirmed per-cell
exclusion overrides changed no metric, so none are configurable.

Writes per repo:
    repos/<repo>/sonar_results.json

Format of sonar_results.json (one entry per condition/model/run):
    {
      "nl/claude/run0": {
        "project_key": "kapitoshk4__library-service-api:nl:claude:run0",
        "bugs": 0,
        "vulnerabilities": 0,
        "code_smells": 5,
        "ncloc": 120,
        "cognitive_complexity": 10,
        "duplicated_lines_density": 0.0,
        "error": null
      },
      ...
    }
"""

import glob
import json
import os
import re
import subprocess
import time
import requests

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────── Config ───────────────────────────

SONAR_URL = os.environ.get("SONAR_URL", "http://localhost:9000")
SONAR_TOKEN = os.environ.get("SONAR_TOKEN", "")
CONTAINER_NAME = "sonarqube"
SCANNER_JAR = "/opt/sonarqube/lib/scanner/sonar-scanner-engine-shaded-26.4.0.121862-all.jar"
JAVA_BIN = "/opt/java/openjdk/bin/java"

REPOS_DIR = os.path.join(os.path.dirname(__file__), "repos")
CONDITIONS = ["nl", "uml"]
MODELS = ["claude", "deepseek", "gemini", "gpt"]

EXPECTED_RUNS = 10
WAIT_TIMEOUT = 600

# Applied to EVERY folder scan.
DEFAULT_DIR_EXCLUSIONS = [
    "**/generated_code(original).py",
    "**/__pycache__/**",
    "**/migrations/**",
    "**/db.sqlite3",
    "**/manage.py",
    "**/*.md",
    "**/templates/**",
    "**/*.html",
    "**/*.js",
    "**/*.jsx",
    "**/*.ts",
    "**/*.tsx",
    "**/*.css",
    "**/*.scss",
]

METRICS = [
    "bugs",
    "vulnerabilities",
    "code_smells",
    "ncloc",
    "lines",
    "complexity",
    "cognitive_complexity",
    "duplicated_lines_density",
    "comment_lines_density",
]


class ScanNotMeasured(RuntimeError):
    """A scan completed but measured nothing (parse failure or empty source)."""


# ─────────────────────────── SonarQube API helpers ───────────────────────────

def _auth():
    """Builds the requests auth tuple for the SonarQube web API.

    Returns:
        tuple[str, str]: The token as the username, with an empty password,
            which is how SonarQube expects token authentication.
    """
    return (SONAR_TOKEN, "")


def create_project(project_key: str, project_name: str):
    """Creates a SonarQube project, tolerating one that already exists.

    Args:
        project_key (str): Unique project key, "<repo>:<condition>:<model>:run<N>".
        project_name (str): Human-readable name shown in the SonarQube UI.

    Raises:
        requests.HTTPError: If the API returns anything other than 200 or 400.
            400 means the project already exists, which is expected on a
            re-run and is not an error: the scan that follows still records a
            new analysis against the existing project.
    """
    r = requests.post(
        f"{SONAR_URL}/api/projects/create",
        params={"project": project_key, "name": project_name},
        auth=_auth(),
    )
    if r.status_code not in (200, 400):
        r.raise_for_status()
    # 400 means already exists — that's fine


def get_metrics(project_key: str) -> dict:
    """Reads the METRICS measures from a project's most recent analysis.

    Args:
        project_key (str): The project key to read measures for.

    Returns:
        dict: Metric name to value, numeric where the value parses as a number
            (int when integral, else float) and left as a string otherwise.
            Metrics the analysis did not produce are absent rather than zero.

    Raises:
        requests.HTTPError: If the measures API call fails.
    """
    r = requests.get(
        f"{SONAR_URL}/api/measures/component",
        params={"component": project_key, "metricKeys": ",".join(METRICS)},
        auth=_auth(),
    )
    r.raise_for_status()
    data = r.json()
    measures = data.get("component", {}).get("measures", [])
    result = {}
    for m in measures:
        key = m["metric"]
        val = m.get("value", m.get("bestValue"))
        try:
            val = float(val)
            if val == int(val):
                val = int(val)
        except (TypeError, ValueError):
            pass
        result[key] = val
    return result


def wait_for_analysis(project_key: str, task_id: str, timeout: int = 600):
    """Polls a Compute Engine task until it finishes.

    A submitted scan is queued: its measures are not readable until the CE
    task reaches SUCCESS.

    Args:
        project_key (str): Project the task belongs to, used in the timeout message.
        task_id (str): CE task ID returned by run_scanner().
        timeout (int, optional): Maximum wait in seconds. Defaults to 600.

    Returns:
        bool: True once the task reaches SUCCESS.

    Raises:
        RuntimeError: If the task ends in FAILED or CANCELLED.
        TimeoutError: If the task has not finished within `timeout` seconds.
        requests.HTTPError: If a poll request fails.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(
            f"{SONAR_URL}/api/ce/task",
            params={"id": task_id},
            auth=_auth(),
        )
        r.raise_for_status()
        status = r.json().get("task", {}).get("status", "")
        if status == "SUCCESS":
            return True
        if status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"SonarQube analysis task {status}")
        time.sleep(3)
    raise TimeoutError(f"Analysis timed out after {timeout}s for {project_key}")

# ─────────────────────────── Scanner runner ───────────────────────────

def run_scanner(project_key: str, source_path: str, is_dir: bool = False,
                exclusions: list[str] | None = None) -> str:
    """Copies the source into the sonarqube container and runs the scanner.

    Args:
        project_key (str): Namespaces the container-side source.
        source_path (str): A single .py file, or a project directory.
        is_dir (bool, optional): True when `source_path` is a project tree.
        exclusions (list[str] | None, optional): sonar.exclusions glob
            patterns, applied only to directory scans. Defaults to None.

    Returns:
        str: The CE task ID of the submitted analysis, to be passed to
            wait_for_analysis() before reading measures.

    Raises:
        RuntimeError: If the scanner exits non-zero, or its output contains no
            task ID.
        subprocess.CalledProcessError: If copying the source into the
            container fails.
    """
    safe_key = project_key.replace(":", "_")
    container_src_dir = f"/tmp/scan/{safe_key}"
    container_work_dir = f"/tmp/sonar-work/{safe_key}"

    # Step1: Clean src dir so stale files from a prior run don't leak in
    subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "sh", "-c",
         f"rm -rf {container_src_dir} {container_work_dir}; "
         f"mkdir -p {container_src_dir} {container_work_dir} /tmp/sonar-home"],
        check=True, capture_output=True,
    )

    # Step2: Copy into container via stdin (docker cp doesn't work with named volumes on macOS)
    if is_dir:
        # COPYFILE_DISABLE keeps macOS tar from injecting ._ AppleDouble files
        tar = subprocess.run(
            ["tar", "-C", source_path, "-cf", "-", "."],
            check=True, capture_output=True,
            env={**os.environ, "COPYFILE_DISABLE": "1"},
        )
        subprocess.run(
            ["docker", "exec", "-i", CONTAINER_NAME,
             "sh", "-c", f"tar -C {container_src_dir} -xf -"],
            input=tar.stdout, check=True, capture_output=True,
        )
    else:
        with open(source_path, "rb") as f:
            subprocess.run(
                ["docker", "exec", "-i", CONTAINER_NAME,
                 "sh", "-c", f"cat > {container_src_dir}/generated_code.py"],
                input=f.read(), check=True, capture_output=True,
            )

    import json as _json
    params = {
        "sonar.projectKey": project_key,
        "sonar.sources": container_src_dir,
        "sonar.projectBaseDir": container_src_dir,
        "sonar.working.directory": container_work_dir,
        "sonar.host.url": "http://localhost:9000",
        "sonar.scm.disabled": "true",
        "sonar.language": "py",
        "sonar.python.version": "3",
    }
    if exclusions:
        params["sonar.exclusions"] = ",".join(exclusions)
    scanner_params = _json.dumps(params)

    # Step3: Execute Scan in the container
    cmd = [
        "docker", "exec",
        "-e", f"SONAR_TOKEN={SONAR_TOKEN}",
        "-e", f"SONARQUBE_SCANNER_PARAMS={scanner_params}",
        CONTAINER_NAME,
        JAVA_BIN, "-Duser.home=/tmp/sonar-home",
        "-jar", SCANNER_JAR,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    combined = result.stdout + result.stderr

    if result.returncode != 0:
        raise RuntimeError(f"Scanner failed:\n{combined[-2000:]}")

    # Extract task ID from scanner JSON output line:
    import re as _re
    for line in combined.splitlines():
        m = _re.search(r'task\?id=([0-9a-f-]{36})', line)
        if m:
            return m.group(1)

    raise RuntimeError("Could not find task ID in scanner output")


# ─────────────────────────── Main pipeline ───────────────────────────

_RUN_FILE_RE = re.compile(r"\.run(\d+)\.py$")
_RUN_DIR_RE = re.compile(r"\.run(\d+)$")


def discover_runs(repo_dir: str, condition: str, model: str) -> list[tuple[int, str, bool]]:
    """Finds every generation run of one (repo, condition, model) cell.

    A run is delivered either as a single file <model>.run<N>.py or as a
    multi-file project folder <model>.run<N>/.

    Args:
        repo_dir (str): Path to the repo directory under repos/.
        condition (str): "nl" or "uml".
        model (str): One of MODELS.

    Returns:
        list[tuple[int, str, bool]]: (run_index, path, is_dir) per run, sorted
            by run index. Empty when the cell has no runs on disk.
    """
    oc = os.path.join(repo_dir, condition, "outputcode")
    runs = []
    for path in glob.glob(os.path.join(oc, f"{model}.run*.py")):
        m = _RUN_FILE_RE.search(os.path.basename(path))
        if m:
            runs.append((int(m.group(1)), path, False))
    for path in glob.glob(os.path.join(oc, f"{model}.run*")):
        if not os.path.isdir(path):
            continue
        m = _RUN_DIR_RE.search(os.path.basename(path))
        if m:
            runs.append((int(m.group(1)), path, True))
    return sorted(runs)


def _scan_one(repo: str, condition: str, model: str, run: int,
              source_path: str, is_dir: bool, exclusions) -> tuple[str, dict]:
    """Creates, scans and reads the measures of one generation run.

    Args:
        repo (str): Repo folder name under repos/.
        condition (str): "nl" or "uml".
        model (str): One of MODELS.
        run (int): Run index.
        source_path (str): File or directory holding this run's code.
        is_dir (bool): True when `source_path` is a project tree.
        exclusions (list[str] | None): sonar.exclusions patterns for a
            directory scan, or None for a single-file scan.

    Returns:
        tuple[str, dict]: The "<condition>/<model>/run<N>" result key, and the metrics dict.
    """
    key = f"{condition}/{model}/run{run}"
    project_key = f"{repo}:{condition}:{model}:run{run}"
    project_name = f"{repo} / {condition} / {model} / run{run}"

    tag = " (dir scan)" if is_dir else ""
    print(f"  [{key}] creating project {project_key!r}{tag} ...", end=" ", flush=True)
    try:
        create_project(project_key, project_name)
        print("scanning ...", end=" ", flush=True)
        task_id = run_scanner(project_key, source_path, is_dir=is_dir, exclusions=exclusions)
        print(f"waiting (task={task_id[:8]}) ...", end=" ", flush=True)
        wait_for_analysis(project_key, task_id, timeout=WAIT_TIMEOUT)
        metrics = get_metrics(project_key)
        metrics["project_key"] = project_key
        if not metrics.get("ncloc"):
            raise ScanNotMeasured(
                "no_ncloc: parse failure or empty file (nothing analysed)")
        metrics["error"] = None
        print("done")
        return key, metrics
    except Exception as exc:
        print(f"ERROR: {exc}")
        return key, {"project_key": project_key, "error": str(exc)}


def analyze_repo(repo: str) -> dict:
    """Scans every run of every condition x model cell of one repo.

    Args:
        repo (str): Repo folder name under repos/.

    Returns:
        dict: "<condition>/<model>/run<N>" to that run's metrics dict, in the
            shape written to repos/<repo>/sonar_results.json.
    """
    repo_dir = os.path.join(REPOS_DIR, repo)
    results = {}

    for condition in CONDITIONS:
        for model in MODELS:
            for run, source_path, is_dir in discover_runs(repo_dir, condition, model):
                k, metrics = _scan_one(
                    repo, condition, model, run, source_path,
                    is_dir=is_dir,
                    exclusions=DEFAULT_DIR_EXCLUSIONS if is_dir else None,
                )
                results[k] = metrics

    return results


def main():
    if not SONAR_TOKEN:
        raise SystemExit(
            "ABORT: SONAR_TOKEN is not set. Add it to .env (see .env.example):\n"
            "  SONAR_TOKEN=<your SonarQube user token>"
        )

    repos = sorted(r for r in os.listdir(REPOS_DIR)
                   if os.path.isdir(os.path.join(REPOS_DIR, r)))

    n_cells = len(repos) * len(CONDITIONS) * len(MODELS)
    print(f"{len(repos)} repos x {len(CONDITIONS)} conditions x {len(MODELS)} models "
          f"= {n_cells} cells x {EXPECTED_RUNS} runs = {n_cells * EXPECTED_RUNS} scans\n")

    expected_keys = [f"{c}/{m}/run{r}"
                     for c in CONDITIONS for m in MODELS for r in range(EXPECTED_RUNS)]

    problems = []
    for repo in repos:
        print(f"\n=== {repo} ===")
        results = analyze_repo(repo)

        problems += [f"{repo}/{k}: {m['error']}"
                     for k, m in results.items() if m.get("error")]
        problems += [f"{repo}/{k}: missing — no .run<N>.py or .run<N>/ on disk"
                     for k in expected_keys if k not in results]

        out_path = os.path.join(REPOS_DIR, repo, "sonar_results.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  → saved {out_path}")

    total = n_cells * EXPECTED_RUNS
    print(f"\n{total - len(problems)}/{total} runs measured.")
    if problems:
        print(f"\nINCOMPLETE ({len(problems)}):")
        for p in problems:
            print(f"  {p}")


if __name__ == "__main__":
    main()
