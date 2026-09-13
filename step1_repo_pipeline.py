"""
Usage:
    python step1_repo_pipeline.py https://github.com/owner/repo
    python step1_repo_pipeline.py owner/repo
    python step1_repo_pipeline.py <url1> <url2> ...

Creates:
    repos/<owner>__<repo>/
        <repo>-main/         ← extracted repo source code
        nl/
            input/           ← place description.txt here manually
            outputcode/      ← step 2 writes generated code here
            tests/           ← ask opus to generate test suites here
        uml/
            input/           ← place classes.puml here manually
            outputcode/      ← step 2 writes generated code here
            tests/           ← ask opus to generate test suites here
"""

import argparse
import io
import os
import re
import sys
import zipfile

import requests

REPOS = os.path.join(os.path.dirname(__file__), "repos")

SCAFFOLD_DIRS = [
    "nl/input",
    "nl/outputcode",
    "nl/tests",
    "uml/input",
    "uml/outputcode",
    "uml/tests",
]


def parse_github_url(raw: str) -> tuple[str, str]:
    raw = raw.strip().rstrip("/")
    # Accept full URL or shorthand owner/repo
    m = re.match(r"(?:https?://github\.com/)?([^/]+)/([^/]+?)(?:\.git)?$", raw)
    if not m:
        raise ValueError(f"Cannot parse as GitHub repo: {raw!r}")
    return m.group(1), m.group(2)


def download_zip(owner: str, repo: str) -> bytes:
    for branch in ("main", "master"):
        url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        print(f"  Trying {url} ...")
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            return r.content
        print(f"  → {r.status_code}, trying next branch")
    raise RuntimeError(f"Could not download {owner}/{repo} (tried main, master)")


def scaffold(owner: str, repo: str) -> str:
    folder_name = f"{owner}__{repo}"
    dest = os.path.join(REPOS, folder_name)
    os.makedirs(dest, exist_ok=True)

    repo_dest = os.path.join(dest, f"{repo}-main")
    if os.path.isdir(repo_dest):
        print(f"  [skip] repo already extracted at {repo_dest}")
    else:
        zip_bytes = download_zip(owner, repo)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # GitHub zips have a single top-level dir <repo>-<branch>/
            roots = {name.split("/", 1)[0] for name in zf.namelist()}
            if len(roots) != 1:
                raise RuntimeError(f"Unexpected zip layout for {owner}/{repo}: {sorted(roots)}")
            extracted = os.path.join(dest, roots.pop())
            if os.path.exists(extracted):
                raise RuntimeError(f"Refusing to overwrite existing {extracted}")
            zf.extractall(dest)
        if extracted != repo_dest:
            os.rename(extracted, repo_dest)
        print(f"  Extracted → {repo_dest}")

    for subdir in SCAFFOLD_DIRS:
        os.makedirs(os.path.join(dest, subdir), exist_ok=True)

    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download GitHub repos and scaffold repos/ structure."
    )
    parser.add_argument(
        "repos",
        nargs="+",
        metavar="URL_OR_OWNER/REPO",
        help="GitHub repo URL or owner/repo shorthand",
    )
    args = parser.parse_args()

    os.makedirs(REPOS, exist_ok=True)

    for raw in args.repos:
        try:
            owner, repo = parse_github_url(raw)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            continue

        print(f"\n→ {owner}/{repo}")
        try:
            dest = scaffold(owner, repo)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            continue

        folder = os.path.basename(dest)
        print(f"  Ready: repos/{folder}/")
        print(f"  Next steps:")
        print(f"    1. Place description.txt  →  repos/{folder}/nl/input/description.txt")
        print(f"    2. Place classes.puml      →  repos/{folder}/uml/input/classes.puml")
        print(f"    3. Run: python step2_code_generation.py --repo {folder}")


if __name__ == "__main__":
    main()
