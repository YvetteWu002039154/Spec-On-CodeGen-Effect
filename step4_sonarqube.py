"""
Step 4 — Run SonarQube analysis on each generated_code.py and collect metrics.

Usage:
    python step4_sonarqube.py                     # all repos
    python step4_sonarqube.py --repo kapitoshk4__library-service-api
    python step4_sonarqube.py --repo foo --condition nl
    python step4_sonarqube.py --repo foo --models claude gpt

Analyzes files at:
    thesis_repos/<repo>/nl/outputcode/<model>/generated_code.py
    thesis_repos/<repo>/uml/outputcode/<model>/generated_code.py

Uses the sonarqube container's bundled scanner JAR (no local Java needed).

Writes per repo:
    thesis_repos/<repo>/sonar_results.json

Format of sonar_results.json:
    {
      "nl/claude": {
        "project_key": "kapitoshk4__library-service-api:nl:claude",
        "bugs": 0,
        "vulnerabilities": 0,
        "code_smells": 5,
        "sqale_rating": "A",
        "reliability_rating": "A",
        "security_rating": "A",
        "ncloc": 120,
        "cognitive_complexity": 10,
        "duplicated_lines_density": 0.0,
        "error": null
      },
      ...
    }
"""

import argparse
import json
import os
import subprocess
import time
import requests

# ── Config ────────────────────────────────────────────────────────────────────

SONAR_URL = "http://localhost:9000"
SONAR_TOKEN = "squ_ea14639b33cb0cd8d14b2f6e5f54309c5a4f44f1"
CONTAINER_NAME = "sonarqube"
SCANNER_JAR = "/opt/sonarqube/lib/scanner/sonar-scanner-engine-shaded-26.4.0.121862-all.jar"
JAVA_BIN = "/opt/java/openjdk/bin/java"

REPOS_DIR = os.path.join(os.path.dirname(__file__), "thesis_repos")
SPECIAL_CASES_DIR = os.path.join(os.path.dirname(__file__), "special_cases")
CONDITIONS = ["nl", "uml"]
MODELS = ["claude", "deepseek", "gemini", "gpt"]

METRICS = [
    "bugs",
    "vulnerabilities",
    "code_smells",
    "sqale_rating",
    "reliability_rating",
    "security_rating",
    "ncloc",
    "lines",
    "cognitive_complexity",
    "duplicated_lines_density",
    "comment_lines_density",
]

RATING_MAP = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}


# ── SonarQube API helpers ─────────────────────────────────────────────────────

def _auth():
    return (SONAR_TOKEN, "")


def create_project(project_key: str, project_name: str):
    r = requests.post(
        f"{SONAR_URL}/api/projects/create",
        params={"project": project_key, "name": project_name},
        auth=_auth(),
    )
    if r.status_code not in (200, 400):
        r.raise_for_status()
    # 400 means already exists — that's fine


def get_metrics(project_key: str) -> dict:
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
        # Convert rating numbers to letters
        if key.endswith("_rating") and val in RATING_MAP:
            val = RATING_MAP[val]
        else:
            # Try numeric conversion
            try:
                val = float(val)
                if val == int(val):
                    val = int(val)
            except (TypeError, ValueError):
                pass
        result[key] = val
    return result


def wait_for_analysis(project_key: str, task_id: str, timeout: int = 120):
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


def get_last_task_id(project_key: str) -> str | None:
    r = requests.get(
        f"{SONAR_URL}/api/ce/component",
        params={"component": project_key},
        auth=_auth(),
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    tasks = r.json().get("queue", []) + r.json().get("current", {}).get("id", [])
    current = r.json().get("current", {})
    return current.get("id")


# ── Scanner runner ────────────────────────────────────────────────────────────

def run_scanner(project_key: str, source_path: str, is_dir: bool = False,
                exclusions: list[str] | None = None) -> str:
    """
    Copies source_path into the sonarqube container and runs the scanner.
    Returns the CE task ID.

    When is_dir is False, source_path is a single generated_code.py file.
    When is_dir is True, source_path is a project tree (special case, e.g. a
    model that emitted a full multi-file project instead of one file); the whole
    tree is tarred into the container and scanned, honoring `exclusions`.

    Uses SONARQUBE_SCANNER_PARAMS (JSON) because the bundled scanner engine
    JAR does not read -D JVM system properties for sonar.* config.
    Requires user.home and sonar.working.directory to be writable /tmp paths
    since /opt/sonarqube and /home/sonarqube are read-only in the container.
    """
    safe_key = project_key.replace(":", "_")
    container_src_dir = f"/tmp/scan/{safe_key}"
    container_work_dir = f"/tmp/sonar-work/{safe_key}"

    # Start from a clean src dir so stale files from a prior run don't leak in
    subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "sh", "-c",
         f"rm -rf {container_src_dir} {container_work_dir}; "
         f"mkdir -p {container_src_dir} {container_work_dir} /tmp/sonar-home"],
        check=True, capture_output=True,
    )

    # Copy into container via stdin (docker cp doesn't work with named volumes on macOS)
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
    # {"level":"INFO","message":"...http://localhost:9000/api/ce/task?id=UUID"}
    import re as _re
    for line in combined.splitlines():
        m = _re.search(r'task\?id=([0-9a-f-]{36})', line)
        if m:
            return m.group(1)

    raise RuntimeError("Could not find task ID in scanner output")


# ── Special cases ─────────────────────────────────────────────────────────────

def load_special_case(repo: str, condition: str, model: str) -> dict | None:
    """
    Look up special_cases/<repo>/<condition>/<model>/config.json.

    Returned dict:
      sources     — path to a project tree to scan, relative to the repo dir
      exclusions  — optional list of sonar.exclusions glob patterns
    Returns None when there is no special case (the normal single-file path).
    """
    cfg = os.path.join(SPECIAL_CASES_DIR, repo, condition, model, "config.json")
    if not os.path.exists(cfg):
        return None
    with open(cfg) as f:
        return json.load(f)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def analyze_repo(repo: str, conditions: list[str], models: list[str]) -> dict:
    repo_dir = os.path.join(REPOS_DIR, repo)
    results = {}

    for condition in conditions:
        for model in models:
            key = f"{condition}/{model}"
            special = load_special_case(repo, condition, model)

            if special:
                source_path = os.path.join(repo_dir, special["sources"])
                exclusions = special.get("exclusions", [])
                is_dir = True
                if not os.path.isdir(source_path):
                    print(f"  [SKIP] {key} — special-case sources dir not found: {source_path}")
                    results[key] = {"error": "special_case_sources_not_found"}
                    continue
            else:
                source_path = os.path.join(
                    repo_dir, condition, "outputcode", model, "generated_code.py"
                )
                exclusions = None
                is_dir = False
                if not os.path.exists(source_path):
                    print(f"  [SKIP] {key} — file not found")
                    results[key] = {"error": "file_not_found"}
                    continue

            project_key = f"{repo}:{condition}:{model}"
            project_name = f"{repo} / {condition} / {model}"

            tag = " (special-case dir scan)" if is_dir else ""
            print(f"  [{key}] creating project {project_key!r}{tag} ...", end=" ", flush=True)
            try:
                create_project(project_key, project_name)
                print("scanning ...", end=" ", flush=True)
                task_id = run_scanner(project_key, source_path, is_dir=is_dir, exclusions=exclusions)
                print(f"waiting (task={task_id[:8]}) ...", end=" ", flush=True)
                wait_for_analysis(project_key, task_id)
                metrics = get_metrics(project_key)
                metrics["project_key"] = project_key
                metrics["error"] = None
                results[key] = metrics
                print("done")
            except Exception as exc:
                print(f"ERROR: {exc}")
                results[key] = {"project_key": project_key, "error": str(exc)}

    return results


def main():
    parser = argparse.ArgumentParser(description="Step 4: SonarQube analysis of generated code")
    parser.add_argument("--repo", help="Specific repo name (default: all)")
    parser.add_argument("--condition", choices=CONDITIONS, help="nl or uml (default: both)")
    parser.add_argument("--models", nargs="+", choices=MODELS, help="Models to analyze")
    args = parser.parse_args()

    repos = [args.repo] if args.repo else sorted(os.listdir(REPOS_DIR))
    conditions = [args.condition] if args.condition else CONDITIONS
    models = args.models if args.models else MODELS

    for repo in repos:
        repo_dir = os.path.join(REPOS_DIR, repo)
        if not os.path.isdir(repo_dir):
            print(f"[WARN] {repo} not found, skipping")
            continue

        print(f"\n=== {repo} ===")
        results = analyze_repo(repo, conditions, models)

        out_path = os.path.join(repo_dir, "sonar_results.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  → saved {out_path}")


if __name__ == "__main__":
    main()
